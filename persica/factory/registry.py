import asyncio
from importlib import import_module
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict

from persica.factory.component import AsyncInitializingComponent, BaseComponent
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory
from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from logging import Logger

    from persica.factory.abstract import AbstractAutowireCapableFactory
    from persica.scanner.path import ClassPathScanner

_LOGGER = get_logger(__name__, "DefinitionRegistry")


class DefinitionRegistry:
    _logger: "Logger" = _LOGGER
    import_module_status: Dict[str, bool] = {}

    def __init__(self, factory: "AbstractAutowireCapableFactory", class_scanner: "ClassPathScanner"):
        self.factory = factory
        self.class_scanner = class_scanner

    def flash(self):
        self._import_module()
        self._registry_class()

    def _import_module(self):
        for module_name in self.class_scanner.get_module("persica.factory.BaseComponent"):
            self.__import_module(module_name)
        for module_name in self.class_scanner.get_module("persica.factory.AsyncInitializingComponent"):
            self.__import_module(module_name)

    def __import_module(self, module_name: str):
        if self.import_module_status.get(module_name) is None:
            self._logger.info("import module %s", module_name)
            try:
                import_module(module_name)
                self.import_module_status.setdefault(module_name, True)
            except Exception as e:
                self.import_module_status.setdefault(module_name, False)
                self._logger.info("import module error %s", module_name)
                raise e

    def _registry_class(self):
        for obj in object.__subclasses__():
            if issubclass(obj, BaseComponent):
                self.factory.object_definition_map.setdefault(obj, ObjectDefinition(obj))
            if issubclass(obj, InterfaceFactory):
                self.factory.object_definition_map.setdefault(obj, ObjectDefinition(obj, True))

    async def initialize(self):
        _futures = []
        for _, value in self.factory.singleton_factory.items():
            if isinstance(value, AsyncInitializingComponent):
                _futures.append(self._run_async(value.initialize))
        for _, value in self.factory.singleton_objects.items():
            if isinstance(value, AsyncInitializingComponent):
                _futures.append(self._run_async(value.initialize))

        await asyncio.gather(*_futures)

    async def shutdown(self):
        _futures = []
        for _, value in self.factory.singleton_factory.items():
            if isinstance(value, AsyncInitializingComponent):
                _futures.append(self._run_async(value.shutdown))
        for _, value in self.factory.singleton_objects.items():
            if isinstance(value, AsyncInitializingComponent):
                _futures.append(self._run_async(value.shutdown))

        await asyncio.gather(*_futures)

    async def _run_async(self, func: Callable[..., Coroutine[Any, Any, Any]]):
        try:
            await func()
        except Exception as e:
            self._logger.error(e)
