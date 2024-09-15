from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.scanner.path import ClassPathScanner


class ApplicationContext:
    def __init__(self, factory: AbstractAutowireCapableFactory, class_scanner: ClassPathScanner):
        self.class_scanner = class_scanner
        self.factory = factory

    def run(self):
        pass

    def __run(self):
        self.class_scanner.parse_directory()

    async def initialize(self):
        pass

    async def shutdown(self) -> None:
        pass
