import logging


def get_logger(file_name: str, class_name: str | None = None) -> logging.Logger:
    name = f"{file_name}.{class_name}"
    return logging.getLogger(name)
