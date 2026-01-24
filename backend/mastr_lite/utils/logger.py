import logging

log = logging.getLogger(__name__)

def setup_logging(level: str = 'INFO') -> None:
    """
    Setup basic logging configuration.

    Parameters
    ----------
    level : str, optional
        Logging level (DEBUG, INFO, WARNING, ERROR), by default 'INFO'
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def setup_logger(name:str = 'mastr-lite'):
    """
    Configure logging for open-MaStR lite.

    Returns
    -------
    logging.Logger
        Logger instance
    """
    setup_logging()
    return logging.getLogger(name=name)
