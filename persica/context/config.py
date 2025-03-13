import sys
from typing import TYPE_CHECKING, ClassVar

from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from logging import Logger

if sys.version_info >= (3, 11):
    import tomllib
else:
    import toml as tomllib


_LOGGER = get_logger(__name__, "PyProjectConfig")


class PyProjectConfig:
    _logger: "Logger" = _LOGGER
    data: ClassVar[dict] = {}

    def __init__(self):
        self.reload()

    @classmethod
    def reload(cls):
        try:
            with open("pyproject.toml", "rb") as f:
                cls.data = tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            # 处理文件不存在或解析错误
            cls._logger.error("Error loading pyproject.toml", exc_info=e)
            cls.data = {}

    def get_import_packages(self):
        data = self.data.get("persica", {}).get("import-packages", [])
        if not self._is_list_of_str(data):
            raise TypeError("import-packages must be a list of strings")
        return data

    @staticmethod
    def _is_list_of_str(obj):
        return isinstance(obj, list) and all(isinstance(item, str) for item in obj)
