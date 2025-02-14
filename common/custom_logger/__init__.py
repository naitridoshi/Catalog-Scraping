import logging
import queue
import sys
from logging.handlers import QueueListener
from time import sleep

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


def get_logger(name: str = 'util'):
    logger = logging.getLogger(name)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_format)

    # Remove all handlers associated with the logger
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)
    log_queue = queue.Queue()
    queue_handler = logging.handlers.QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    # Use console_handler only in the listener
    listener = QueueListener(
        log_queue, console_handler, respect_handler_level=True
    )
    return logger, listener


if __name__ == '__main__':
    test_logger, test_listener = get_logger("test")
    test_listener.start()
    test_logger.info('Test')
    sleep(1)
