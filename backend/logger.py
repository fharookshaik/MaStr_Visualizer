import logging
import os
from dotenv import load_dotenv

load_dotenv()

def setup_logging(level: str = 'INFO') -> logging.Logger:
    """
    Setup centralized logging configuration for the backend.

    Parameters
    ----------
    level : str, optional
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL), by default 'INFO'
        Can be overridden by LOG_LEVEL environment variable

    Returns
    -------
    logging.Logger
        Configured logger instance for the backend
    """
    log_level = os.getenv('LOG_LEVEL', level).upper()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler()  # Output to stdout/stderr for Docker
        ]
    )

    # Create and return logger for backend
    logger = logging.getLogger('mastr_visualizer_backend')
    return logger

# Global logger instance
logger = setup_logging()
