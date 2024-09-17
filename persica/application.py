import asyncio
import platform
import signal
from typing import TYPE_CHECKING, Optional, Sequence

from persica.context.application import ApplicationContext
from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.scanner.path import ClassPathScanner
from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from logging import Logger

_LOGGER = get_logger(__name__, "DefinitionRegistry")


class Application:
    _logger: "Logger" = _LOGGER

    def __init__(
        self,
        loop: "Optional[AbstractEventLoop]" = None,
    ) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self.factory = AbstractAutowireCapableFactory()
        self.class_scanner = ClassPathScanner()
        self.context = ApplicationContext(factory=self.factory, class_scanner=self.class_scanner)

    def run(self) -> None:
        self.context.run()
        self.__run()

    def __run(self, stop_signals: Optional[Sequence[int]] = None) -> None:
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
