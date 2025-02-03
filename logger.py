import os
import queue
import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from datetime import datetime, timezone
from config import LOGGER_APP_NAME


def create_folder_if_not_exists(folder_path):
    """
     Creates a folder at the specified path if it does not already exist.

    Args:
        folder_path (str): The path to the folder to be created.

    Raises:
        OSError: If the folder cannot be created due to system-related issues.
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


"""Configures logging for the application.

Sets up a logger named 'webapp' to print logging messages to the console.
Logs messages at the DEBUG level or higher.

Example log message format: 2023-11-21 15:30:00 - DEBUG - This is a debug message.
"""


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        record.auditAt = str(
            datetime.fromtimestamp(record.created, timezone.utc)
        )

        colors = {
            'levelname': COLORS.get(record.levelname, COLORS['RESET']),
            'auditAt': COLORS.get('AUDIT_AT', COLORS['RESET'])
        }
        colored_attrs = {
            attr: f"{colors[attr]}{getattr(record, attr)}{COLORS['RESET']}"
            for attr in colors
        }

        formatted_record = super().format(record)
        for attr, colored_value in colored_attrs.items():
            formatted_record = formatted_record.replace(
                getattr(record, attr), colored_value
            )
        return formatted_record


COLORS = {
    'AUDIT_AT': '\033[36m',
    'DEBUG': '\033[94m',
    'INFO': '\033[1;32m',
    'WARNING': '\033[33m',
    'ERROR': '\033[1;31m',
    'CRITICAL': '\033[4;1;31m',
    'REQUEST_INIT': '\033[1;96m',
    'FUNCTION_INVOKE': '\033[35m',
    'FUNCTION_RETURN': '\033[32m',
    'REQUEST_END': '\033[1;96m',
    'QUALNAME': '\033[94m',
    'RESET': '\033[0;0;37m'
}


console_format = ColoredFormatter(
    fmt=' '.join(
        [
            '%(auditAt)s',
            '%(name)s',
            '%(levelname)s ',
            'message: %(message)s'
        ]
    )
)

logger_path = os.path.join("logs")
create_folder_if_not_exists(logger_path)
log_file_path = os.path.join("logs", f"{LOGGER_APP_NAME}.log")


console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(console_format)


# File logging setup
file_handler = RotatingFileHandler(
    log_file_path, maxBytes=10*1024*1024, backupCount=5
)
file_handler.setLevel(logging.DEBUG)

# Plain text format for file logging
file_format = logging.Formatter(
    '%(auditAt)s - %(name)s - %(levelname)s - message: %(message)s'
)

file_handler.setFormatter(file_format)


logger = logging.getLogger(LOGGER_APP_NAME)

logger.setLevel(logging.DEBUG)

log_queue = queue.Queue()

queue_handler = QueueHandler(log_queue)

logger.addHandler(queue_handler)

listener = QueueListener(
    log_queue, console_handler, file_handler, respect_handler_level=True
)

listener.start()
