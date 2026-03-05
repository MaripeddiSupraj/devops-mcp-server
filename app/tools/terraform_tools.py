from app.utils.logger import logger
from app.utils.shell import run_command
import os

def terraform_plan(directory: str) -> dict:
    """
    Run terraform plan in a specified directory.
    Returns the output or any errors.
    """
    logger.info(f"Running terraform plan in: {directory}")
    
    if not os.path.exists(directory):
        return {"error": f"Directory does not exist: {directory}"}
        
    try:
        # First ensure terraform init is run
        logger.debug(f"Running terraform init in {directory}")
        run_command(["terraform", "init", "-no-color"], cwd=directory)
        
        # Then run the plan
        logger.debug(f"Running terraform plan in {directory}")
        output = run_command(["terraform", "plan", "-no-color"], cwd=directory)
        
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
    if not os.path.exists(directory):
        return {"error": f"Directory does not exist: {directory}"}
        
    try:
        output = run_command(["terraform", "state", "list"], cwd=directory)
        return {"status": "success", "resources": output.splitlines()}
    except Exception as e:
        logger.error(f"Terraform state list failed: {e}")
        return {"status": "error", "message": str(e)}

def terraform_show(directory: str) -> dict:
    """
    Show the full current state or plan in JSON format.
    """
    logger.info(f"Running terraform show in: {directory}")
    if not os.path.exists(directory):
        return {"error": f"Directory does not exist: {directory}"}
        
    try:
        output = run_command(["terraform", "show", "-json"], cwd=directory)
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
    if not os.path.exists(directory):
        return {"error": f"Directory does not exist: {directory}"}
        
    try:
        output = run_command(["terraform", "output", "-json"], cwd=directory)
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
    if not os.path.exists(directory):
        return {"error": f"Directory does not exist: {directory}"}
        
    try:
        run_command(["terraform", "init", "-no-color"], cwd=directory)
        
        cmd = ["terraform", "apply", "-no-color"]
        if auto_approve:
            cmd.append("-auto-approve")
            
        output = run_command(cmd, cwd=directory)
        return {"status": "success", "output": output}
    except Exception as e:
        logger.error(f"Terraform apply failed: {e}")
        return {"status": "error", "message": str(e)}
