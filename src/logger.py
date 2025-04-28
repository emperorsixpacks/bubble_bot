import logging


def get_logger(name: str = "app_logger") -> logging.Logger:
    logger = logging.getLogger(name)

    if (
        not logger.handlers
    ):  # Prevent adding multiple handlers in interactive/debug environments
        logger.setLevel(logging.INFO)

        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
        ch.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(ch)

    return logger
