import sys
from typing import ClassVar

if sys.version_info >= (3, 11):
    import tomllib
else:
    import toml as tomllib


class PyProjectConfig:
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
            print(f"Error loading pyproject.toml: {e}")
            cls.data = {}

    def get_import_packages(self):
        data = self.data.get("persica", {}).get("import-packages", [])
        if not self._is_list_of_str(data):
            raise TypeError("import-packages must be a list of strings")
        return data

    @staticmethod
    def _is_list_of_str(obj):
        return isinstance(obj, list) and all(isinstance(item, str) for item in obj)
