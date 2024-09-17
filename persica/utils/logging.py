import logging
from typing import Optional


def get_logger(file_name: str, class_name: Optional[str] = None) -> logging.Logger:
    name = f"{file_name}.{class_name}"
    return logging.getLogger(name)
