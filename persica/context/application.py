from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from persica.factory.abstract import AbstractAutowireCapableFactory
    from persica.factory.registry import DefinitionRegistry
    from persica.scanner.path import ClassPathScanner


class ApplicationContext:
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
        await self.registry.initialize()

    async def shutdown(self) -> None:
        await self.registry.shutdown()
