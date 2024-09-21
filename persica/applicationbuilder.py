from typing import TYPE_CHECKING, List, Optional, Self, Type

from persica.application import Application
from persica.context.application import ApplicationContext
from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.factory.registry import DefinitionRegistry
from persica.scanner.path import ClassPathScanner

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop


class ApplicationBuilder:
    _application_context_class: Type["ApplicationContext"] = ApplicationContext
    _application_class: Type["Application"] = Application
    _abstract_autowire_capable_factory_class: Type["AbstractAutowireCapableFactory"] = AbstractAutowireCapableFactory
    _class_path_scanner_class: Type["ClassPathScanner"] = ClassPathScanner
    _definition_registry: Type["DefinitionRegistry"] = DefinitionRegistry

    def __init__(self):
        self._loop: "Optional[AbstractEventLoop]" = None
        self._scanner_packages: List[str] = []

    def set_application_context_class(self, __cls: Type["ApplicationContext"]) -> Self:
        self._application_context_class = __cls
        return self

    def set_loop(self, loop: "AbstractEventLoop") -> Self:
        self._loop = loop
        return self

    def set_scanner_package(self, package: str) -> Self:
        self._scanner_packages.append(package)
        return self

    def set_scanner_packages(self, packages: List[str]) -> Self:
        self._scanner_packages.extend(packages)
        return self

    def build(self):
        if len(self._scanner_packages) == 0:
            raise RuntimeError("No scanner packages specified")

        factory = self._abstract_autowire_capable_factory_class()
        class_scanner = self._class_path_scanner_class(self._scanner_packages)
        registry = self._definition_registry(factory, class_scanner)
        application: "Application" = self._application_class(
            factory=factory,
            class_scanner=class_scanner,
            registry=registry,
            context_class=self._application_context_class,
            loop=self._loop,
        )
        return application
