import logging
from typing import Optional


def get_logger(file_name: str, class_name: Optional[str] = None) -> logging.Logger:
    """
    Returns a logger with an appropriate name based on the provided file name and optional class name.
    The logger is configured to differentiate log outputs based on the context provided by the file name and class.

    Usage example:

    logger = get_logger(__name__)

    :param file_name:
        The name of the file where the logger is used. This is typically the `__name__` attribute of the module
        or file. The file name is expected to follow a convention, where parts are separated by underscores.
        For example, "myapp_utils" or "myapp_module".

    :param class_name:
        An optional string representing the name of the class where the logger is used.
        If no class name is provided, the logger will attempt to construct a name from the file name.
        If `class_name` is provided, it will append it to the base file name to make the logger name more specific.

    :return:
        A `logging.Logger` instance with a name based on the provided `file_name` and optional `class_name`.

    The logger name generation logic is as follows:
    - If the second part of the `file_name` (split by underscore) starts with "utils" and `class_name` is `None`,
      the logger name is constructed using the first part of the `file_name`.
    - If a `class_name` is provided, the logger name will be a combination of the first part of the `file_name`
      and the provided `class_name`.
    - Otherwise, the second part of the `file_name` is capitalized and used to create the logger name.
    """
    parts = file_name.split("_")
    if parts[1].startswith("utils") and class_name is None:
        name = parts[0].rstrip(".")
    else:
        name = f"{parts[0]}{class_name or parts[1].capitalize()}"
    return logging.getLogger(name)
