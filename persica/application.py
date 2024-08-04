import logging
import platform
import signal
from typing import Optional, TYPE_CHECKING, Sequence

import asyncio

from persica.context.application import ApplicationContext
from persica.context.scanner import ClassScanner
from persica.factory.abstract import AbstractAutowireCapableFactory

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop


class Application:

    def __init__(self, loop: "Optional[AbstractEventLoop]" = None, ) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.context = ApplicationContext()
        self.factory = AbstractAutowireCapableFactory()
        self.class_scanner = ClassScanner(self.factory)

    def run(self) -> None:
        pass

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
            self.logger.info("Interrupt received! shutting down...")
        except Exception as e:
            self.logger.error("Exception raised:", exc_info=e)
        finally:
            self.loop.run_until_complete(self.shutdown())

    @staticmethod
    def _raise_system_exit() -> None:
        raise SystemExit()

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass
