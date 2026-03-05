from app.utils.logger import logger
from app.utils.shell import run_command
import os

def _validate_directory(directory: str) -> str | None:
    if not directory:
        return None

    resolved = os.path.realpath(os.path.abspath(directory))
    if not os.path.isdir(resolved):
        return None

    allowed_roots_env = os.getenv("TERRAFORM_ALLOWED_ROOTS", "").strip()
    if not allowed_roots_env:
        return resolved

    allowed_roots = [
        os.path.realpath(os.path.abspath(path.strip()))
        for path in allowed_roots_env.split(",")
        if path.strip()
    ]
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

def terraform_apply(directory: str, auto_approve: bool = False) -> dict:
    """
    Run terraform apply in a specified directory.
    DANGEROUS: If auto_approve is True, it will apply without requiring a human to type 'yes'.
    """
    logger.info(f"Running terraform apply (auto_approve={auto_approve}) in: {directory}")
    safe_directory = _validate_directory(directory)
    if not safe_directory:
        return {
            "status": "error",
            "message": (
                f"Invalid terraform directory: {directory}. "
                "Directory must exist and be inside TERRAFORM_ALLOWED_ROOTS (if configured)."
            )
        }

    if not auto_approve:
        return {
            "status": "error",
            "message": (
                "Terraform apply without auto_approve is interactive and unsupported in MCP. "
                "Run plan first, then call apply with auto_approve=true only when explicitly authorized."
            )
        }
        
    try:
        run_command(["terraform", "init", "-no-color", "-input=false"], cwd=safe_directory)
        
        cmd = ["terraform", "apply", "-no-color", "-input=false", "-auto-approve"]
            
        output = run_command(cmd, cwd=safe_directory)
        return {"status": "success", "output": output}
    except Exception as e:
        logger.error(f"Terraform apply failed: {e}")
        return {"status": "error", "message": str(e)}
