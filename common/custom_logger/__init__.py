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


def get_logger(name: str = 'util'):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_format)

    # Create log directory if it doesn't exist
    base_dir = sys.path[1]
    logger_path = os.path.join(base_dir, "logs")
    makedirs(logger_path, exist_ok=True)

    # Thread-safe rotating file handler
    file_handler = ConcurrentRotatingFileHandler(
        join(logger_path, "history.log"),
        maxBytes=10 * 1024 ** 2,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_format)

    # Create a queue and handlers
    log_queue = queue.Queue()
    queue_handler = QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    listener = QueueListener(
        log_queue, console_handler, file_handler, respect_handler_level=True
    )

    return logger, listener


if __name__ == '__main__':
    test_logger, test_listener = get_logger("test")
    test_listener.start()

    test_logger.info('Test message for thread-safe logging')

    sleep(1)
    test_listener.stop()  # Properly stop the listener when done
