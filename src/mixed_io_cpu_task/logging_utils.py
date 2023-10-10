import logging
from pythonjsonlogger import jsonlogger
import time

TIMESTAMP = time.time()


def configure_logger(logger):
    logger.setLevel(level=logging.DEBUG)
    file_handler = logging.FileHandler(f"serial_{TIMESTAMP}.log")
    file_handler.setLevel(level=logging.DEBUG)
    formatter = jsonlogger.JsonFormatter("%(asctime)%(levelname)%(name)%(message)")
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
