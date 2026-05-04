import asyncio

from persica import inject
from persica.application import Application
from persica.context.application import ApplicationContext
from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.factory.definition import ObjectDefinition
from persica.factory.registry import DefinitionRegistry
from persica.scanner.path import ClassPathScanner
from tests.repeated_run_publish_package.components import RepeatedRunPublishedResourceConsumer
from tests.repeated_run_publish_package.shared import RepeatedRunPublishedResource


class _NoOpScanner:
    def flash(self) -> None:
        return None


class _NoOpRegistry:
    def flash(self) -> None:
        return None


class AppPublishedResource:
    pass


class AppPublishedResourceConsumer:
    resource: AppPublishedResource = inject()


class PublishingApplication(Application):
    def __init__(self, *args, **kwargs):
        self.resource = AppPublishedResource()
        super().__init__(*args, **kwargs)

    def provide_objects(self) -> list[AppPublishedResource]:
        return [self.resource]


class RepeatedPublishingApplication(Application):
    def __init__(self, *args, **kwargs):
        self.resource = RepeatedRunPublishedResource("first")
        super().__init__(*args, **kwargs)

    def provide_objects(self) -> list[RepeatedRunPublishedResource]:
        return [self.resource]


class TestApplicationContext:
    async def test_initialize_and_shutdown(self, app):
        loop = asyncio.get_event_loop()
        context = app.context
        await loop.run_in_executor(None, context.run)
        await context.initialize()
        await context.shutdown()


def test_application_provide_objects_defaults_to_empty_list():
    app = Application(
        factory=AbstractAutowireCapableFactory(),
        class_scanner=_NoOpScanner(),
        registry=_NoOpRegistry(),
        context_class=ApplicationContext,
    )

    assert app.provide_objects() == []


def test_application_publishes_resources_for_component_injection():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        AppPublishedResourceConsumer: ObjectDefinition(class_object=AppPublishedResourceConsumer)
    }
    app = PublishingApplication(
        factory=factory,
        class_scanner=_NoOpScanner(),
        registry=_NoOpRegistry(),
        context_class=ApplicationContext,
    )

    consumer = factory.create_object(AppPublishedResourceConsumer)

    assert consumer.resource is app.resource
    assert factory.published_objects == {AppPublishedResource: [app.resource]}
    assert factory.published_object_sequence == [app.resource]


def test_context_run_replaces_application_published_resources_between_runs():
    factory = AbstractAutowireCapableFactory()
    scanner = ClassPathScanner(default_base_packages=["tests.repeated_run_publish_package"])
    registry = DefinitionRegistry(factory, scanner)
    app = RepeatedPublishingApplication(
        factory=factory,
        class_scanner=scanner,
        registry=registry,
        context_class=ApplicationContext,
    )

    app.context.run()

    first_consumer = factory.singleton_objects[RepeatedRunPublishedResourceConsumer]
    first_resource = app.resource
    assert first_consumer.resource is first_resource

    app.resource = RepeatedRunPublishedResource("second")

    app.context.run()

    second_consumer = factory.singleton_objects[RepeatedRunPublishedResourceConsumer]
    assert second_consumer is not first_consumer
    assert second_consumer.resource is app.resource
    assert second_consumer.resource is not first_resource
    assert factory.published_objects == {RepeatedRunPublishedResource: [app.resource]}
    assert factory.published_object_sequence == [app.resource]
