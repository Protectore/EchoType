import logging
from rich.logging import RichHandler
from rich.console import Console


LOG_LEVEL = logging.ERROR


def get_logger(name, log_file_name="EchoType.log"):
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(LOG_LEVEL)

    # Log file handler
    file_handler = logging.FileHandler(log_file_name, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(file_handler)


    # Cool console handler
    rich_handler = RichHandler(
        console=Console(stderr=True),
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    rich_handler.addFilter(lambda record: record.exc_info is None)
    logger.addHandler(rich_handler)

    return logger
