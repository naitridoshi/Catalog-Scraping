import logging
import os
import queue
import sys
from logging.handlers import QueueListener, QueueHandler
from os import makedirs
from os.path import join
from time import sleep

from concurrent_log_handler import ConcurrentRotatingFileHandler
from common.custom_logger.constants import LogColors
from common.custom_logger.helper import color_string


# Custom formatter to add colors
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_colors = {
            logging.INFO: LogColors.INFO,
            logging.DEBUG: LogColors.DEBUG,
            logging.WARNING: LogColors.WARNING,
            logging.ERROR: LogColors.ERROR,
        }
        color = log_colors.get(record.levelno, LogColors.RESET)
        record.levelname = f"{color}{record.levelname}{LogColors.RESET}"
        return super().format(record)


# Create formatter
console_format = ColoredFormatter(
    fmt=" ".join(
        [
            f"\033[35m%(asctime)s{LogColors.RESET} |",
            "%(name)s |",
            "%(levelname)s |",
            "message: %(message)s"
        ]
    )
)

file_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - message: %(message)s'
)


def get_logger(
    name: str = "utils",
    queue_logs: bool = True,
):
    logger = logging.getLogger(name)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_format)

    # Remove all handlers associated with the logger
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if queue_logs:
        log_queue = queue.Queue()  # type: ignore
        queue_handler = logging.handlers.QueueHandler(log_queue)
        logger.addHandler(queue_handler)
        handlers = list()
        handlers.append(console_handler)

        # Use console_handler only in the listener
        listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
        return logger, listener

    logger.addHandler(console_handler)
    return logger



if __name__ == '__main__':
    test_logger, test_listener = get_logger("test")
    test_listener.start()

    test_logger.info('Test message for thread-safe logging')

    sleep(1)
    test_listener.stop()  # Properly stop the listener when done
