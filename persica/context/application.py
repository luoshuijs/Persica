import asyncio
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from persica.factory.component import AsyncInitializingComponent
from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from logging import Logger

    from persica.factory.abstract import AbstractAutowireCapableFactory
    from persica.factory.registry import DefinitionRegistry
    from persica.scanner.path import ClassPathScanner

_LOGGER = get_logger(__name__, "DefinitionRegistry")


class ApplicationContext:
    _logger: "Logger" = _LOGGER

    def __init__(
        self,
        factory: "AbstractAutowireCapableFactory",
        class_scanner: "ClassPathScanner",
        registry: "DefinitionRegistry",
    ):
        self.class_scanner = class_scanner
        self.factory = factory
        self.registry = registry

    def run(self):
        self.__run()

    def __run(self):
        self.class_scanner.flash()
        self.registry.flash()
        self.factory.instantiate_object()

    async def initialize(self):
        await self._initialize()

    async def shutdown(self) -> None:
        await self._shutdown()

    async def _initialize(self):
        _futures = []
        for _, value in self.factory.singleton_factory.items():
            if isinstance(value, AsyncInitializingComponent):
                _futures.append(self._run_async(value.initialize))
        for _, value in self.factory.singleton_objects.items():
            if isinstance(value, AsyncInitializingComponent):
                _futures.append(self._run_async(value.initialize))

        await asyncio.gather(*_futures)

    async def _shutdown(self):
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
            self._logger.exception(e)
