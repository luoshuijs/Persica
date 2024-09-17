import asyncio
import platform
import signal
from typing import TYPE_CHECKING, Optional, Sequence, Type

from persica.scanner.path import ClassPathScanner
from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from logging import Logger

    from persica.context.application import ApplicationContext
    from persica.factory.abstract import AbstractAutowireCapableFactory
    from persica.factory.registry import DefinitionRegistry

_LOGGER = get_logger(__name__, "DefinitionRegistry")


class Application:
    _logger: "Logger" = _LOGGER

    def __init__(
        self,
        factory: "AbstractAutowireCapableFactory",
        class_scanner: "ClassPathScanner",
        registry: "DefinitionRegistry",
        context_class: Type["ApplicationContext"],
        loop: "Optional[AbstractEventLoop]" = None,
    ) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self.factory = factory
        self.class_scanner = class_scanner
        self.registry = registry
        self.context = context_class(factory=self.factory, class_scanner=self.class_scanner, registry=self.registry)

    def run(self) -> None:
        self._logger.info("Application Run")
        self.context.run()
        self._run()

    def _run(self, stop_signals: Optional[Sequence[int]] = None) -> None:
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
            self._logger.error("Exception raised:", exc_info=e)
        finally:
            self.loop.run_until_complete(self.shutdown())

    @staticmethod
    def _raise_system_exit() -> None:
        raise SystemExit()

    async def initialize(self) -> None:
        await self.context.initialize()

    async def shutdown(self) -> None:
        await self.context.shutdown()
