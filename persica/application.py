import asyncio
import platform
import signal
from collections.abc import Sequence
from typing import TYPE_CHECKING

from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from logging import Logger

    from persica.context.application import ApplicationContext
    from persica.factory.abstract import AbstractAutowireCapableFactory
    from persica.factory.registry import DefinitionRegistry
    from persica.scanner.path import ClassPathScanner

_LOGGER = get_logger(__name__, "DefinitionRegistry")


class Application:
    _logger: "Logger" = _LOGGER

    def __init__(
        self,
        factory: "AbstractAutowireCapableFactory",
        class_scanner: "ClassPathScanner",
        registry: "DefinitionRegistry",
        context_class: type["ApplicationContext"],
        loop: "AbstractEventLoop | None" = None,
    ) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self.factory = factory
        self.class_scanner = class_scanner
        self.registry = registry
        self.context = context_class(factory=self.factory, class_scanner=self.class_scanner, registry=self.registry)
        self.factory.add_external_object(self.context)
        self.factory.add_external_object(self)

    def run(self) -> None:
        self._logger.info("Application Run")
        self.context.run()
        self._run()

    def _run(self, stop_signals: Sequence[int] | None = None) -> None:
        if platform.system() != "Windows":
            stop_signals = (signal.SIGINT, signal.SIGTERM, signal.SIGABRT)
        if stop_signals is not None:
            for sig in stop_signals or []:
                self.loop.add_signal_handler(sig, self._raise_system_exit)
        try:
            self.loop.run_until_complete(self.initialize())
            self.loop.run_forever()
        except (KeyboardInterrupt, SystemExit):
            self._logger.info("Interrupt received! shutting down...")
        except Exception as e:
            self._logger.exception("Exception raised:", exc_info=e)
        finally:
            self.loop.run_until_complete(self.shutdown())

    @staticmethod
    def _raise_system_exit() -> None:
        raise SystemExit

    async def initialize(self) -> None:
        await self.context.initialize()

    async def shutdown(self) -> None:
        await self.context.shutdown()
