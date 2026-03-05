import logging
import sys

def setup_logger():
    """
    Configure standard logging for the application.
    """
    logger = logging.getLogger("devops_mcp")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger

logger = setup_logger()
