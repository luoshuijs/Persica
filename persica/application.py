import asyncio
import platform
import signal
import threading
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
        self.loop = loop
        self._owns_loop = False
        self.factory = factory
        self.class_scanner = class_scanner
        self.registry = registry
        self.context = context_class(factory=self.factory, class_scanner=self.class_scanner, registry=self.registry)
        self.factory.add_external_object(self.context)
        self.factory.add_external_object(self)
        self.factory._publish_objects(self)

    def provide_objects(self) -> list[object]:
        return []

    def run(self) -> None:
        self._logger.info("Application Run")
        self._run()

    def _run(self, stop_signals: Sequence[int] | None = None) -> None:  # noqa: PLR0912
        loop = self._get_runtime_loop()
        if loop.is_running():
            raise RuntimeError("Application.run() requires a configured event loop that is not already running")

        self.context.run()

        primary_error: Exception | None = None
        if platform.system() != "Windows" and threading.current_thread() is threading.main_thread():
            stop_signals = (signal.SIGINT, signal.SIGTERM, signal.SIGABRT)
        if stop_signals is not None:
            for sig in stop_signals or []:
                loop.add_signal_handler(sig, self._raise_system_exit)
        try:
            loop.run_until_complete(self.initialize())
            loop.run_forever()
        except (KeyboardInterrupt, SystemExit):
            self._logger.info("Interrupt received! shutting down...")
        except Exception as e:
            primary_error = e
            self._logger.exception("Exception raised:", exc_info=e)
        finally:
            try:
                loop.run_until_complete(self.shutdown())
            except Exception as shutdown_error:
                if primary_error is None:
                    primary_error = shutdown_error
                else:
                    self._logger.exception("Shutdown raised during error handling", exc_info=shutdown_error)
            finally:
                if self._owns_loop:
                    asyncio.set_event_loop(None)
                    loop.close()
                    self.loop = None
                    self._owns_loop = False

        if primary_error is not None:
            raise primary_error.with_traceback(primary_error.__traceback__)

    def _get_runtime_loop(self) -> "AbstractEventLoop":
        if self.loop is not None:
            return self.loop

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._owns_loop = True

        self.loop = loop
        return loop

    @staticmethod
    def _raise_system_exit() -> None:
        raise SystemExit

    async def initialize(self) -> None:
        await self.context.initialize()

    async def shutdown(self) -> None:
        await self.context.shutdown()
