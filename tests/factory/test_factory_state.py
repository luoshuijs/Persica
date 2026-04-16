from persica import Phase
from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.factory.component import BaseComponent
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory
from persica.factory.registry import DefinitionRegistry
from persica.scanner.path import ClassPathScanner
from tests.sample_registry_root.component_module import RootScannedComponent

REGISTERED_ORDER = 7


class FirstOrderedDependency:
    pass


class SecondOrderedDependency:
    pass


class ConsumerOfOrderedDependencies:
    def __init__(self, first: FirstOrderedDependency, second: SecondOrderedDependency):
        self.first = first
        self.second = second


class RegisteredOrderedDependencyOne(BaseComponent, order=REGISTERED_ORDER):
    pass


class RegisteredOrderedDependencyTwo(BaseComponent, order=REGISTERED_ORDER):
    pass


class RegisteredOrderedConsumer(BaseComponent):
    def __init__(self, first: RegisteredOrderedDependencyOne, second: RegisteredOrderedDependencyTwo):
        self.first = first
        self.second = second


class RegisteredPhasedDependency(BaseComponent, phase=Phase.REPOSITORY):
    pass


class RegisteredPhasedConsumer(BaseComponent, phase=Phase.SERVICE):
    def __init__(self, dependency: RegisteredPhasedDependency):
        self.dependency = dependency


class RegisteredFactoryProduct:
    pass


class RegisteredFactoryBase(InterfaceFactory[RegisteredFactoryProduct]):
    def get_object(self, obj: RegisteredFactoryProduct | None) -> RegisteredFactoryProduct:
        return obj if obj is not None else RegisteredFactoryProduct()


class RegisteredFactoryChild(RegisteredFactoryBase):
    pass


class StalePublishedResource:
    pass


def test_factory_state_is_instance_scoped():
    external = FirstOrderedDependency()
    _first_factory = AbstractAutowireCapableFactory(external_objects=[external])
    second_factory = AbstractAutowireCapableFactory()

    assert second_factory.object_definitions == {}
    assert second_factory.singleton_objects == {}
    assert second_factory.factory_cache == {}
    assert second_factory.external_objects == {}


def test_component_order_keyword_sets_order_attribute():
    component_order = 3

    class OrderedComponent(BaseComponent, order=component_order):
        pass

    assert OrderedComponent.__order__ == component_order


def test_instantiate_all_objects_handles_multiple_definitions_in_same_order_bucket():
    factory = AbstractAutowireCapableFactory()
    first_definition = ObjectDefinition(class_object=FirstOrderedDependency)
    second_definition = ObjectDefinition(class_object=SecondOrderedDependency)
    consumer_definition = ObjectDefinition(class_object=ConsumerOfOrderedDependencies)
    factory.order_definitions = {1: [first_definition, second_definition]}
    factory.object_definitions = {
        FirstOrderedDependency: first_definition,
        SecondOrderedDependency: second_definition,
        ConsumerOfOrderedDependencies: consumer_definition,
    }

    factory.instantiate_all_objects()

    assert isinstance(factory.singleton_objects.get(FirstOrderedDependency), FirstOrderedDependency)
    assert isinstance(factory.singleton_objects.get(SecondOrderedDependency), SecondOrderedDependency)
    consumer = factory.singleton_objects.get(ConsumerOfOrderedDependencies)
    assert isinstance(consumer, ConsumerOfOrderedDependencies)
    assert isinstance(consumer.first, FirstOrderedDependency)
    assert isinstance(consumer.second, SecondOrderedDependency)


def test_registry_registration_supports_ordered_component_instantiation():
    factory = AbstractAutowireCapableFactory()
    scanner = ClassPathScanner(default_base_packages=["tests.factory"])
    scanner.flash()
    registry = DefinitionRegistry(factory, scanner)

    registry.flash()
    factory.instantiate_all_objects()

    bucket = factory.order_definitions[REGISTERED_ORDER]
    assert isinstance(bucket, list)
    assert {definition.class_object for definition in bucket} == {
        RegisteredOrderedDependencyOne,
        RegisteredOrderedDependencyTwo,
    }
    consumer = factory.singleton_objects.get(RegisteredOrderedConsumer)
    assert isinstance(consumer, RegisteredOrderedConsumer)
    assert isinstance(consumer.first, RegisteredOrderedDependencyOne)
    assert isinstance(consumer.second, RegisteredOrderedDependencyTwo)


def test_registry_registration_supports_phased_component_instantiation():
    factory = AbstractAutowireCapableFactory()
    scanner = ClassPathScanner(default_base_packages=["tests.factory"])
    scanner.flash()
    registry = DefinitionRegistry(factory, scanner)

    registry.flash()
    factory.instantiate_all_objects()

    repository_bucket = factory.order_definitions[Phase.REPOSITORY]
    service_bucket = factory.order_definitions[Phase.SERVICE]
    assert {definition.class_object for definition in repository_bucket} == {RegisteredPhasedDependency}
    assert {definition.class_object for definition in service_bucket} == {RegisteredPhasedConsumer}
    consumer = factory.singleton_objects.get(RegisteredPhasedConsumer)
    assert isinstance(consumer, RegisteredPhasedConsumer)
    assert isinstance(consumer.dependency, RegisteredPhasedDependency)


def test_definition_registry_import_state_is_instance_scoped():
    factory = AbstractAutowireCapableFactory()
    scanner = ClassPathScanner(default_base_packages=[])
    first_registry = DefinitionRegistry(factory, scanner)
    second_registry = DefinitionRegistry(factory, scanner)

    first_registry.import_module_status["tests.factory.test_factory"] = True

    assert second_registry.import_module_status == {}


def test_definition_registry_preserves_factory_flag_for_nested_factory_subclasses():
    factory = AbstractAutowireCapableFactory()
    scanner = ClassPathScanner(default_base_packages=["tests.factory"])
    scanner.flash()
    registry = DefinitionRegistry(factory, scanner)

    registry.flash()

    definition = factory.object_definitions.get(RegisteredFactoryChild)
    assert definition is not None
    assert definition.is_factory is True


def test_registry_flash_replaces_factory_registrations_between_scan_roots():
    factory = AbstractAutowireCapableFactory()
    scanner = ClassPathScanner(default_base_packages=[])
    registry = DefinitionRegistry(factory, scanner)

    scanner.flash(base_packages=["tests.factory"])
    registry.flash()

    assert RegisteredOrderedDependencyOne in factory.object_definitions
    assert REGISTERED_ORDER in factory.order_definitions

    scanner.flash(base_packages=["tests.sample_registry_root"])
    registry.flash()

    assert factory.object_definitions == {RootScannedComponent: factory.object_definitions[RootScannedComponent]}
    assert REGISTERED_ORDER not in factory.order_definitions
    assert {definition.class_object for definition in factory.order_definitions[0]} == {RootScannedComponent}


def test_registry_flash_clears_published_resources():
    factory = AbstractAutowireCapableFactory()
    scanner = ClassPathScanner(default_base_packages=["tests.sample_registry_root"])
    scanner.flash()
    registry = DefinitionRegistry(factory, scanner)
    stale_resource = StalePublishedResource()
    factory.published_objects = {StalePublishedResource: [stale_resource]}
    factory.published_object_sequence = [stale_resource]

    registry.flash()

    assert StalePublishedResource not in factory.published_objects
    assert factory.published_object_sequence == []
