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
