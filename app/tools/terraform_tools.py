from app.utils.logger import logger
from app.utils.shell import run_command
from app.utils.audit import audit_event
from app.utils.approval import validate_approval_token
from app.config import settings
import os

def _validate_directory(directory: str) -> str | None:
    if not directory:
        return None

    resolved = os.path.realpath(os.path.abspath(directory))
    if not os.path.isdir(resolved):
        return None

    if settings.terraform_allow_unrestricted:
        return resolved

    allowed_roots = settings.terraform_allowed_roots
    if not allowed_roots:
        return None

    for root in allowed_roots:
        try:
            if os.path.commonpath([resolved, root]) == root:
                return resolved
        except ValueError:
            continue

    return None

def terraform_plan(directory: str) -> dict:
    """
    Run terraform plan in a specified directory.
    Returns the output or any errors.
    """
    logger.info(f"Running terraform plan in: {directory}")
    
    safe_directory = _validate_directory(directory)
    if not safe_directory:
        return {
            "status": "error",
            "message": (
                f"Invalid terraform directory: {directory}. "
                "Directory must exist and be inside TERRAFORM_ALLOWED_ROOTS (if configured)."
            )
        }
        
    try:
        # First ensure terraform init is run
        logger.debug(f"Running terraform init in {safe_directory}")
        run_command(["terraform", "init", "-no-color", "-input=false"], cwd=safe_directory)
        
        # Then run the plan
        logger.debug(f"Running terraform plan in {safe_directory}")
        output = run_command(["terraform", "plan", "-no-color", "-input=false"], cwd=safe_directory)
        
        # In a real environment with huge plans, we might summarize this or parse it,
        # but for now we return the raw plan output.
        return {
            "status": "success",
            "output": output
        }
    except Exception as e:
        logger.error(f"Terraform plan failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

def terraform_state_list(directory: str) -> dict:
    """
    List all tracked resources in the current Terraform state.
    """
    logger.info(f"Running terraform state list in: {directory}")
    safe_directory = _validate_directory(directory)
    if not safe_directory:
        return {
            "status": "error",
            "message": (
                f"Invalid terraform directory: {directory}. "
                "Directory must exist and be inside TERRAFORM_ALLOWED_ROOTS (if configured)."
            )
        }
        
    try:
        run_command(["terraform", "init", "-no-color", "-input=false"], cwd=safe_directory)
        output = run_command(["terraform", "state", "list"], cwd=safe_directory)
        return {"status": "success", "resources": output.splitlines()}
    except Exception as e:
        logger.error(f"Terraform state list failed: {e}")
        return {"status": "error", "message": str(e)}

def terraform_show(directory: str) -> dict:
    """
    Show the full current state or plan in JSON format.
    """
    logger.info(f"Running terraform show in: {directory}")
    safe_directory = _validate_directory(directory)
    if not safe_directory:
        return {
            "status": "error",
            "message": (
                f"Invalid terraform directory: {directory}. "
                "Directory must exist and be inside TERRAFORM_ALLOWED_ROOTS (if configured)."
            )
        }
        
    try:
        run_command(["terraform", "init", "-no-color", "-input=false"], cwd=safe_directory)
        output = run_command(["terraform", "show", "-json"], cwd=safe_directory)
        import json
        return {"status": "success", "state": json.loads(output)}
    except Exception as e:
        logger.error(f"Terraform show failed: {e}")
        return {"status": "error", "message": str(e)}

def terraform_output(directory: str) -> dict:
    """
    Get all output variables from the current Terraform state.
    """
    logger.info(f"Running terraform output in: {directory}")
    safe_directory = _validate_directory(directory)
    if not safe_directory:
        return {
            "status": "error",
            "message": (
                f"Invalid terraform directory: {directory}. "
                "Directory must exist and be inside TERRAFORM_ALLOWED_ROOTS (if configured)."
            )
        }
        
    try:
        run_command(["terraform", "init", "-no-color", "-input=false"], cwd=safe_directory)
        output = run_command(["terraform", "output", "-json"], cwd=safe_directory)
        import json
        return {"status": "success", "outputs": json.loads(output) if output else {}}
    except Exception as e:
        logger.error(f"Terraform output failed: {e}")
        return {"status": "error", "message": str(e)}

def terraform_apply(
    directory: str,
    auto_approve: bool = False,
    approval_reason: str | None = None,
    approval_requested_at_epoch: int | None = None,
    approval_token: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """
    Run terraform apply in a specified directory.
    DANGEROUS: If auto_approve is True, it will apply without requiring a human to type 'yes'.
    """
    logger.info(f"Running terraform apply (auto_approve={auto_approve}) in: {directory}")
    audit_event(
        action="terraform_apply",
        status="attempted",
        details={
            "directory": directory,
            "auto_approve": auto_approve,
            "correlation_id": correlation_id,
        },
    )
    safe_directory = _validate_directory(directory)
    if not safe_directory:
        audit_event(
            action="terraform_apply",
            status="rejected",
            details={
                "directory": directory,
                "reason": "invalid_directory",
                "correlation_id": correlation_id,
            },
        )
        return {
            "status": "error",
            "message": (
                f"Invalid terraform directory: {directory}. "
                "Directory must exist and be inside TERRAFORM_ALLOWED_ROOTS (if configured)."
            )
        }

    if not auto_approve:
        audit_event(
            action="terraform_apply",
            status="rejected",
            details={
                "directory": safe_directory,
                "reason": "interactive_not_supported",
                "correlation_id": correlation_id,
            },
        )
        return {
            "status": "error",
            "message": (
                "Terraform apply without auto_approve is interactive and unsupported in MCP. "
                "Run plan first, then call apply with auto_approve=true only when explicitly authorized."
            )
        }

    if settings.terraform_apply_require_approval:
        if not settings.terraform_apply_approval_secret:
            audit_event(
                action="terraform_apply",
                status="rejected",
                details={
                    "directory": safe_directory,
                    "reason": "approval_secret_missing",
                    "correlation_id": correlation_id,
                },
            )
            return {
                "status": "error",
                "message": "TERRAFORM_APPLY_APPROVAL_SECRET is required when approval gating is enabled."
            }

        if not approval_reason or approval_requested_at_epoch is None or not approval_token:
            audit_event(
                action="terraform_apply",
                status="rejected",
                details={
                    "directory": safe_directory,
                    "reason": "approval_fields_missing",
                    "correlation_id": correlation_id,
                },
            )
            return {
                "status": "error",
                "message": (
                    "approval_reason, approval_requested_at_epoch, and approval_token are required "
                    "for terraform apply."
                ),
            }

        token_is_valid = validate_approval_token(
            secret=settings.terraform_apply_approval_secret,
            directory=safe_directory,
            requested_at_epoch=approval_requested_at_epoch,
            reason=approval_reason,
            provided_token=approval_token,
            ttl_seconds=settings.terraform_apply_token_ttl_seconds,
        )
        if not token_is_valid:
            audit_event(
                action="terraform_apply",
                status="rejected",
                details={
                    "directory": safe_directory,
                    "reason": "approval_token_invalid_or_expired",
                    "approval_requested_at_epoch": approval_requested_at_epoch,
                    "correlation_id": correlation_id,
                },
            )
            return {
                "status": "error",
                "message": "approval_token is invalid or expired for terraform apply.",
            }
        
    try:
        run_command(["terraform", "init", "-no-color", "-input=false"], cwd=safe_directory)
        
        cmd = ["terraform", "apply", "-no-color", "-input=false", "-auto-approve"]
            
        output = run_command(cmd, cwd=safe_directory)
        audit_event(
            action="terraform_apply",
            status="success",
            details={
                "directory": safe_directory,
                "auto_approve": True,
                "approval_reason": approval_reason,
                "approval_requested_at_epoch": approval_requested_at_epoch,
                "correlation_id": correlation_id,
            },
        )
        return {"status": "success", "output": output}
    except Exception as e:
        logger.error(f"Terraform apply failed: {e}")
        audit_event(
            action="terraform_apply",
            status="error",
            details={
                "directory": safe_directory,
                "error": str(e),
                "correlation_id": correlation_id,
            },
        )
        return {"status": "error", "message": str(e)}
