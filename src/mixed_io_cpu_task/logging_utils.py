import logging
from pythonjsonlogger import jsonlogger


def configure_logger(logger, filename: str):
    logger.setLevel(level=logging.DEBUG)
    file_handler = logging.FileHandler(f"{filename}.log", mode="w")
    file_handler.setLevel(level=logging.DEBUG)
    formatter = jsonlogger.JsonFormatter("%(asctime)%(levelname)%(name)%(message)")
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
