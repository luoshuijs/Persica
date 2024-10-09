import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

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
        self.factory.instantiate_all_objects()

    async def initialize(self):
        await self._process_components("initialize")

    async def shutdown(self) -> None:
        await self._process_components("shutdown")

    async def _process_components(self, method_name: str):
        components_by_order = defaultdict(list)

        for component_dict in [self.factory.singleton_factories, self.factory.singleton_objects]:
            for value in component_dict.values():
                if isinstance(value, AsyncInitializingComponent):
                    method = getattr(value, method_name)
                    components_by_order[value.__order__].append(self._run_async(method))

        for order in sorted(components_by_order.keys()):
            tasks = components_by_order[order]
            await asyncio.gather(*tasks)

    async def _run_async(self, func: Callable[..., Coroutine[Any, Any, Any]]):
        try:
            await func()
        except Exception as e:
            self._logger.exception("Run Error", exc_info=e)
