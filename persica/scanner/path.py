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
        self.scanned_modules: list[str] = []
        if default_base_packages is None:
            default_base_packages = []
        self.default_base_packages = default_base_packages

    def flash(self, base_packages: list[str] | None = None):
        self.class_graph = ClassGraph()
        self.scanned_modules = []
        if base_packages is None:
            base_packages = []
        base_packages = base_packages or self.default_base_packages
        if base_packages is not None:
            for base_package in base_packages:
                self.parse_base_package(base_package)

    def parse_base_package(self, base_package: str):
        package_spec = find_spec(base_package)
        if package_spec is None:
            return

        is_package = package_spec.submodule_search_locations is not None
        if package_spec.origin is not None:
            self._parse_module(base_package, package_spec.origin, is_package=is_package)

        if not is_package:
            return

        for module_info in walk_packages(package_spec.submodule_search_locations, prefix=base_package + "."):
            mod_spec = find_spec(module_info.name)
            if mod_spec is None or mod_spec.origin is None:
                continue

            if mod_spec.origin == "built-in":
                continue

            self._parse_module(
                module_info.name,
                mod_spec.origin,
                is_package=mod_spec.submodule_search_locations is not None,
            )

    def _parse_module(self, module_name: str, origin: str, is_package: bool):
        if origin == "built-in":
            return

        self._logger.info("Find module: %s", module_name)
        self.scanned_modules.append(module_name)

        try:
            with open(origin, encoding="utf-8") as file:
                source = file.read()
        except (OSError, FileNotFoundError):
            return

        try:
            tree = ast.parse(source, filename=origin)
        except SyntaxError as exc:
            self._logger.error("ast parse error", exc_info=exc)
            return

        visitor = ClassVisitor(self.class_graph, module_name, is_package=is_package)
        visitor.visit(tree)

    def get_modules_to_import(self, superclass_name: str) -> set[str]:
        try:
            return self.class_graph.get_modules_to_import(superclass_name)
        except NetworkXError as exc:
            if "is not in the digraph" in str(exc):
                return set()
            raise RuntimeError("Get Modules Error") from exc
