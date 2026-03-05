import subprocess
import logging

logger = logging.getLogger(__name__)

def run_command(cmd: list[str], cwd: str = None, timeout_seconds: int = 120) -> str:
    """
    Run a shell command safely using subprocess.
    Returns the stdout if successful, raises an Exception on failure.
    """
    logger.debug(f"Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout_seconds
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout_seconds}s")
        raise RuntimeError(f"Command timed out after {timeout_seconds}s: {' '.join(cmd)}") from e
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        raise RuntimeError(f"Command execution failed: {e.stderr.strip() or e.stdout.strip()}")
