import ast
from importlib.util import find_spec
from pkgutil import walk_packages
from typing import TYPE_CHECKING

from networkx import NetworkXError

from persica.scanner.graph import ClassGraph
from persica.scanner.visitor import ClassVisitor
from persica.utils.logging import get_logger

_LOGGER = get_logger(__name__, "ClassPathScanner")

if TYPE_CHECKING:
    from logging import Logger


class ClassPathScanner:
    _logger: "Logger" = _LOGGER

    def __init__(self, default_base_packages: list[str] | None = None):
        self.class_graph = ClassGraph()
        if default_base_packages is None:
            default_base_packages = []
        self.default_base_packages = default_base_packages

    def flash(self, base_packages: list[str] | None = None):
        if base_packages is None:
            base_packages = []
        base_packages = base_packages or self.default_base_packages
        if base_packages is not None:
            for base_package in base_packages:
                self.parse_base_package(base_package)

    def parse_base_package(self, base_package: str):
        package_spec = find_spec(base_package)
        if package_spec is None or package_spec.submodule_search_locations is None:
            return

        # 使用 walk_packages 遍历包中的所有模块
        for module_info in walk_packages(package_spec.submodule_search_locations, prefix=base_package + "."):
            # 获取模块规范
            mod_spec = find_spec(module_info.name)
            if mod_spec is None or mod_spec.origin is None:
                continue

            # 跳过内置模块和没有源文件的模块
            if mod_spec.origin == "built-in":
                continue

            self._logger.info("Find module: %s", module_info.name)

            # 读取模块的源代码
            try:
                with open(mod_spec.origin, encoding="utf-8") as file:
                    source = file.read()
            except (OSError, FileNotFoundError):
                continue

            # 解析源代码为 AST
            try:
                tree = ast.parse(source, filename=mod_spec.origin)
            except SyntaxError as exc:
                # 处理语法错误
                self._logger.exception("ast parse error", exc_info=exc)
                continue

            # 创建 ClassVisitor 实例 并访问 AST
            visitor = ClassVisitor(self.class_graph, module_info.name)
            visitor.visit(tree)

    def get_modules_to_import(self, superclass_name: str) -> set[str]:
        try:
            return self.class_graph.get_modules_to_import(superclass_name)
        except NetworkXError as exc:
            if "is not in the digraph" in str(exc):
                return set()
            raise RuntimeError("Get Modules Error") from exc
