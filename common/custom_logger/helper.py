from common.custom_logger.constants import Colors


def color_string(message, color: Colors = Colors.CYAN):
    return f"{color.value}{str(message)}{Colors.RESET.value}"
