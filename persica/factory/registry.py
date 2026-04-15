import inspect
from importlib import import_module
from typing import TYPE_CHECKING

from persica.factory.component import BaseComponent
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory
from persica.scanner.graph import LoadOrderConflictError
from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from logging import Logger

    from persica.factory.abstract import AbstractAutowireCapableFactory
    from persica.scanner.path import ClassPathScanner

_LOGGER = get_logger(__name__, "DefinitionRegistry")


class DefinitionRegistry:
    _logger: "Logger" = _LOGGER

    def __init__(self, factory: "AbstractAutowireCapableFactory", class_scanner: "ClassPathScanner"):
        self.factory = factory
        self.class_scanner = class_scanner
        self.import_module_status: dict[str, bool] = {}

    def flash(self):
        self.import_module_status = {}
        self.factory.object_definitions = {}
        self.factory.order_definitions = {}
        self.factory.factory_cache = {}
        self.factory.singleton_objects = {}
        self.factory.singleton_factories = {}
        self._import_module()
        self._registry_class()
        self._check_class()

    def _import_module(self):
        for module_name in self._get_framework_modules():
            self.__import_module(module_name)

    def __import_module(self, module_name: str):
        if self.import_module_status.get(module_name) is None:
            self._logger.info("import module %s", module_name)
            try:
                import_module(module_name)
                self.import_module_status.setdefault(module_name, True)
            except Exception:
                self.import_module_status.setdefault(module_name, False)
                self._logger.error("import module error %s", module_name)  # noqa: TRY400
                raise

    def _registry_class(self):
        for module_name, imported in self.import_module_status.items():
            if not imported:
                continue
            module = import_module(module_name)
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if cls.__module__ != module_name:
                    continue
                if issubclass(cls, BaseComponent):
                    self._register_class(cls)
                elif issubclass(cls, InterfaceFactory):
                    self._register_class(cls, is_factory=True)

    def _register_class(self, cls: type[object], is_factory: bool | None = None):
        definition = ObjectDefinition(cls, is_factory)
        if hasattr(cls, "__order__"):
            __order__: int = cls.__order__
            class_name = f"{cls.__module__}.{cls.__name__}"
            self.class_scanner.class_graph.set_order(class_name, __order__)
            self.factory.order_definitions.setdefault(__order__, []).append(definition)
        self.factory.object_definitions.setdefault(cls, definition)

    def _get_framework_modules(self) -> set[str]:
        modules = self.class_scanner.get_modules_to_import("persica.factory.component.BaseComponent")
        modules.update(self.class_scanner.get_modules_to_import("persica.factory.component.AsyncInitializingComponent"))
        modules.update(self.class_scanner.get_modules_to_import("persica.factory.interface.InterfaceFactory"))
        modules.update(self._get_seeded_framework_modules())
        return modules

    def _get_seeded_framework_modules(self) -> set[str]:
        modules: set[str] = set()
        scanned_modules = set(self.class_scanner.scanned_modules)
        for class_name, module_name in self.class_scanner.class_graph.class_to_module.items():
            if module_name not in scanned_modules:
                continue
            if not self.class_scanner.class_graph.graph.has_node(class_name):
                continue
            parent_names = set(self.class_scanner.class_graph.graph.predecessors(class_name))
            for parent_name in parent_names:
                if parent_name in self.class_scanner.class_graph.class_to_module:
                    continue
                parent_class = self._resolve_runtime_class(parent_name)
                if parent_class is None:
                    continue
                if issubclass(parent_class, BaseComponent) or issubclass(parent_class, InterfaceFactory):
                    modules.update(self.class_scanner.get_modules_to_import(class_name))
                    break
        return modules

    def _resolve_runtime_class(self, class_name: str) -> type[object] | None:
        module_name, _, attribute_name = class_name.rpartition(".")
        if not module_name or not attribute_name:
            return None
        try:
            module = import_module(module_name)
        except Exception:
            return None
        candidate = getattr(module, attribute_name, None)
        if isinstance(candidate, type):
            return candidate
        return None

    def _check_class(self):
        conflicts = self.class_scanner.class_graph.check_conflict()
        if conflicts:
            raise LoadOrderConflictError(conflicts)
