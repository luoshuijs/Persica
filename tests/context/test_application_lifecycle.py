import asyncio
import gc
import threading

import pytest

from persica.applicationbuilder import ApplicationBuilder
from persica.context.application import ApplicationContext
from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.factory.registry import DefinitionRegistry
from persica.scanner.path import ClassPathScanner
from tests.lifecycle_failure_package import events as init_failure_events
from tests.lifecycle_failure_package import reset_events as reset_init_failure_events
from tests.lifecycle_package import events as lifecycle_events
from tests.lifecycle_package import reset_events as reset_lifecycle_events
from tests.lifecycle_rescan_package import events as lifecycle_rescan_events
from tests.lifecycle_rescan_package import reset_events as reset_lifecycle_rescan_events
from tests.lifecycle_same_order_failure_package import events as same_order_init_failure_events
from tests.lifecycle_same_order_failure_package import get_initialize_gate
from tests.lifecycle_same_order_failure_package import reset_events as reset_same_order_init_failure_events
from tests.run_failure_package import events as run_failure_events
from tests.run_failure_package import reset_events as reset_run_failure_events
from tests.run_lifecycle_package import events as run_lifecycle_events
from tests.run_lifecycle_package import reset_events as reset_run_lifecycle_events
from tests.shutdown_failure_package import events as shutdown_failure_events
from tests.shutdown_failure_package import reset_events as reset_shutdown_failure_events


class TestApplicationLifecycle:
    def test_build_does_not_require_current_event_loop(self):
        result: dict[str, object] = {}

        def build_application() -> None:
            try:
                asyncio.set_event_loop(None)
                result["app"] = ApplicationBuilder().set_scanner_package("tests.lifecycle_package").build()
            except Exception as exc:
                result["error"] = exc

        thread = threading.Thread(target=build_application)
        thread.start()
        thread.join()

        assert "error" not in result
        assert result["app"] is not None

    @pytest.mark.asyncio
    async def test_initialize_and_shutdown_follow_component_order(self):
        reset_lifecycle_events()
        app = ApplicationBuilder().set_scanner_package("tests.lifecycle_package").build()

        await asyncio.get_running_loop().run_in_executor(None, app.context.run)
        await app.initialize()
        await app.shutdown()

        assert lifecycle_events == [
            "initialize:default",
            "initialize:early",
            "initialize:late",
            "shutdown:late",
            "shutdown:early",
            "shutdown:default",
        ]

    @pytest.mark.asyncio
    async def test_initialize_failure_is_raised_to_caller(self):
        reset_init_failure_events()
        app = ApplicationBuilder().set_scanner_package("tests.lifecycle_failure_package").build()

        await asyncio.get_running_loop().run_in_executor(None, app.context.run)

        with pytest.raises(RuntimeError, match="initialize failed"):
            await app.initialize()

        assert init_failure_events == ["initialize:success", "initialize:failure"]

    @pytest.mark.asyncio
    async def test_initialize_failure_cancels_same_order_siblings_before_shutdown(self):
        reset_same_order_init_failure_events()
        app = ApplicationBuilder().set_scanner_package("tests.lifecycle_same_order_failure_package").build()

        await asyncio.get_running_loop().run_in_executor(None, app.context.run)

        with pytest.raises(RuntimeError, match="same-order initialize failed"):
            await app.initialize()

        await app.shutdown()
        get_initialize_gate().set()
        await asyncio.sleep(0)

        assert "initialize:blocking:finished" not in same_order_init_failure_events
        assert "initialize:blocking:cancelled" in same_order_init_failure_events
        assert same_order_init_failure_events.index(
            "initialize:blocking:cancelled"
        ) < same_order_init_failure_events.index("shutdown:blocking")

    @pytest.mark.asyncio
    async def test_shutdown_attempts_all_components_before_raising(self):
        reset_shutdown_failure_events()
        app = ApplicationBuilder().set_scanner_package("tests.shutdown_failure_package").build()

        await asyncio.get_running_loop().run_in_executor(None, app.context.run)

        with pytest.raises(RuntimeError, match=r"Application shutdown failed with 2 error\(s\)") as exc_info:
            await app.shutdown()

        assert shutdown_failure_events == [
            "shutdown:last",
            "shutdown:middle",
            "shutdown:first",
        ]
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, asyncio.CancelledError)

    @pytest.mark.asyncio
    async def test_rescan_replaces_lifecycle_singletons(self):
        reset_lifecycle_events()
        reset_lifecycle_rescan_events()

        factory = AbstractAutowireCapableFactory()
        scanner = ClassPathScanner(["tests.lifecycle_package"])
        registry = DefinitionRegistry(factory, scanner)
        context = ApplicationContext(factory=factory, class_scanner=scanner, registry=registry)

        await asyncio.get_running_loop().run_in_executor(None, context.run)
        await context.initialize()
        await context.shutdown()

        reset_lifecycle_events()
        reset_lifecycle_rescan_events()
        scanner.default_base_packages = ["tests.lifecycle_rescan_package"]

        await asyncio.get_running_loop().run_in_executor(None, context.run)
        await context.initialize()
        await context.shutdown()

        assert lifecycle_events == []
        assert lifecycle_rescan_events == ["initialize:rescan", "shutdown:rescan"]

    def test_run_creates_loop_without_current_event_loop_and_stops_cleanly(self):
        reset_run_lifecycle_events()
        result: dict[str, object] = {}

        def run_application() -> None:
            try:
                asyncio.set_event_loop(None)
                app = ApplicationBuilder().set_scanner_package("tests.run_lifecycle_package").build()
                app.run()
                result["app"] = app
            except BaseException as exc:
                result["error"] = exc

        thread = threading.Thread(target=run_application)
        thread.start()
        thread.join()

        assert "error" not in result
        assert run_lifecycle_events == ["initialize", "shutdown"]

    def test_run_propagates_initialize_failure(self):
        reset_run_failure_events()
        result: dict[str, object] = {}

        def run_application() -> None:
            try:
                asyncio.set_event_loop(None)
                app = ApplicationBuilder().set_scanner_package("tests.run_failure_package").build()
                app.run()
            except BaseException as exc:
                result["error"] = exc

        thread = threading.Thread(target=run_application)
        thread.start()
        thread.join()

        assert isinstance(result.get("error"), RuntimeError)
        assert str(result["error"]) == "run initialize failed"
        assert run_failure_events == ["initialize", "shutdown"]

    def test_run_skips_signal_registration_in_non_main_thread_on_non_windows(self, monkeypatch):
        reset_run_lifecycle_events()
        result: dict[str, object] = {"signal_calls": 0}
        original_new_event_loop = asyncio.new_event_loop

        monkeypatch.setattr("persica.application.platform.system", lambda: "Linux")

        def instrumented_new_event_loop():
            loop = original_new_event_loop()

            def fail_add_signal_handler(*args, **kwargs):
                result["signal_calls"] = int(result["signal_calls"]) + 1
                raise AssertionError("signal handlers must not be registered in non-main threads")

            loop.add_signal_handler = fail_add_signal_handler
            return loop

        monkeypatch.setattr("persica.application.asyncio.new_event_loop", instrumented_new_event_loop)

        def run_application() -> None:
            try:
                asyncio.set_event_loop(None)
                app = ApplicationBuilder().set_scanner_package("tests.run_lifecycle_package").build()
                app.run()
            except BaseException as exc:
                result["error"] = exc

        thread = threading.Thread(target=run_application)
        thread.start()
        thread.join()

        assert "error" not in result
        assert result["signal_calls"] == 0
        assert run_lifecycle_events == ["initialize", "shutdown"]

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings(
        "error:coroutine 'Application\\.(initialize|shutdown)' was never awaited:RuntimeWarning"
    )
    @pytest.mark.filterwarnings("error::pytest.PytestUnraisableExceptionWarning")
    async def test_run_with_running_configured_loop_fails_without_coroutine_warnings(self, recwarn):
        reset_run_lifecycle_events()
        app = (
            ApplicationBuilder()
            .set_loop(asyncio.get_running_loop())
            .set_scanner_package("tests.run_lifecycle_package")
            .build()
        )
        calls: list[str] = []

        def fail_class_scanner_flash() -> None:
            calls.append("class_scanner.flash")

        def fail_registry_flash() -> None:
            calls.append("registry.flash")

        def fail_factory_instantiate_all_objects() -> None:
            calls.append("factory.instantiate_all_objects")

        app.class_scanner.flash = fail_class_scanner_flash
        app.registry.flash = fail_registry_flash
        app.factory.instantiate_all_objects = fail_factory_instantiate_all_objects

        with pytest.raises(RuntimeError, match="already running"):
            app.run()

        gc.collect()

        runtime_warnings = [warning for warning in recwarn if issubclass(warning.category, RuntimeWarning)]
        assert calls == []
        assert runtime_warnings == []
        assert run_lifecycle_events == []
