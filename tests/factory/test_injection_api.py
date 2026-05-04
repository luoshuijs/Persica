import pytest

from persica import inject, inject_all, inject_map
from persica.error import AmbiguousDependencyException, InvalidInjectionConfigurationError
from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory


class PropertyDependency:
    pass


class ExactPropertyDependency(PropertyDependency):
    pass


class AlternatePropertyDependency(PropertyDependency):
    pass


class PropertyTarget:
    dependency: PropertyDependency = inject()

    def __init__(self):
        self.observed_dependency = None

    def after_inject(self):
        self.observed_dependency = self.dependency


class BaseInjectedPropertyTarget:
    dependency: ExactPropertyDependency = inject()


class OverrideSuppressesInjectedPropertyTarget(BaseInjectedPropertyTarget):
    dependency = None


class UnresolvedForwardReferenceMixin:
    pass


class NarrowAnnotationPropertyTarget(UnresolvedForwardReferenceMixin):
    dependency: ExactPropertyDependency = inject()


class InheritedMarkerBaseTarget:
    dependency: PropertyDependency = inject()


class InheritedMarkerNarrowTarget(InheritedMarkerBaseTarget):
    dependency: ExactPropertyDependency


class InheritedMarkerExactBaseTarget:
    dependency: ExactPropertyDependency = inject()


class InheritedMarkerWideTarget(InheritedMarkerExactBaseTarget):
    dependency: PropertyDependency


class InheritedMarkerMixin:
    dependency: ExactPropertyDependency


class InheritedMarkerMultipleInheritanceTarget(InheritedMarkerMixin, InheritedMarkerBaseTarget):
    pass


UnresolvedForwardReferenceMixin.__annotations__ = {"broken": "DoesNotExist"}


class CollectionDependency:
    def __init__(self, name: str, key: str | None = None):
        self.name = name
        self.key = key


class SingletonCollectedDependency(CollectionDependency):
    pass


class ExternalCollectedDependency(CollectionDependency):
    pass


class PublishedCollectedDependency(CollectionDependency):
    pass


class AlternatePublishedCollectedDependency(CollectionDependency):
    pass


class BroadPublishedCollectedDependency(PublishedCollectedDependency):
    pass


class NarrowPublishedCollectedDependency(BroadPublishedCollectedDependency):
    pass


class NarrowCollectionDependency(CollectionDependency):
    pass


class NarrowCollectionDependencyExtra:
    pass


class RegisteredCollectedDependency(CollectionDependency):
    def __init__(self):
        super().__init__(name="registered", key="registered")


class EarlyOrderedCollectedDependency(CollectionDependency):
    def __init__(self):
        super().__init__(name="registered-early", key="registered-early")


class LateOrderedCollectedDependency(CollectionDependency):
    def __init__(self):
        super().__init__(name="registered-late", key="registered-late")


class MissingKeyCollectedDependency(CollectionDependency):
    pass


class OrderedCollectionPublisher:
    def __init__(self):
        self.first = PublishedCollectedDependency(name="published-first", key="published-first")
        self.second = PublishedCollectedDependency(name="published-second", key="published-second")

    def provide_objects(self) -> list[PublishedCollectedDependency]:
        return [self.first, self.second]


class HeterogeneousCollectionPublisher:
    def __init__(self):
        self.first = PublishedCollectedDependency(name="published-first", key="published-first")
        self.second = AlternatePublishedCollectedDependency(name="published-second", key="published-second")
        self.third = PublishedCollectedDependency(name="published-third", key="published-third")

    def provide_objects(self) -> list[CollectionDependency]:
        return [self.first, self.second, self.third]


class BroadlyAnnotatedSubtypeCollectionPublisher:
    instantiated = False

    def __init__(self):
        type(self).instantiated = True
        self.published = NarrowPublishedCollectedDependency(name="published-narrow", key="published-narrow")

    def provide_objects(self) -> list[CollectionDependency]:
        return [self.published]


class NarrowCollectionConsumer:
    dependencies: list[NarrowPublishedCollectedDependency] = inject_all()


class NarrowKeyedCollectionConsumer:
    dependencies: dict[str, NarrowPublishedCollectedDependency] = inject_map("key")


class BrokenBroadlyAnnotatedSubtypeCollectionPublisher:
    instantiated = False

    def __init__(self):
        type(self).instantiated = True
        self.published = NarrowPublishedCollectedDependency(name="published-narrow", key="published-narrow")

    def provide_objects(self):
        return [self.published]


BrokenBroadlyAnnotatedSubtypeCollectionPublisher.provide_objects.__annotations__ = {
    "return": "BrokenContainer[BroadPublishedCollectedDependency]"
}


class TooBroadObjectCollectionPublisher:
    instantiated = False

    def __init__(self):
        type(self).instantiated = True
        self.published = object()

    def provide_objects(self) -> list[object]:
        return [self.published]


class NameOverlapCollectionDependency(CollectionDependency):
    pass


class NameOverlapCollectionDependencyExtra(CollectionDependency):
    pass


class BrokenNameOverlapCollectionPublisher:
    def provide_objects(self):
        return []


BrokenNameOverlapCollectionPublisher.provide_objects.__annotations__ = {
    "return": "BrokenContainer[NameOverlapCollectionDependencyExtra]"
}


class NameOverlapCollectionConsumer:
    dependencies: list[NameOverlapCollectionDependency] = inject_all()


class OrderedCollectionConsumer:
    dependencies: list[CollectionDependency] = inject_all()


class KeyedCollectionConsumer:
    dependencies: dict[str, CollectionDependency] = inject_map("key")


class DuplicateKeyCollectionPublisher:
    def __init__(self):
        self.first = PublishedCollectedDependency(name="published-duplicate", key="duplicate")
        self.second = PublishedCollectedDependency(name="published-other", key="published-other")

    def provide_objects(self) -> list[PublishedCollectedDependency]:
        return [self.first, self.second]


class MissingKeyCollectionPublisher:
    def __init__(self):
        self.published = MissingKeyCollectedDependency(name="missing-key")

    def provide_objects(self) -> list[MissingKeyCollectedDependency]:
        return [self.published]


class NoneKeyCollectionPublisher:
    def __init__(self):
        self.published = PublishedCollectedDependency(name="none-key", key=None)

    def provide_objects(self) -> list[PublishedCollectedDependency]:
        return [self.published]


class InvalidAllAnnotationConsumer:
    dependencies: tuple[CollectionDependency, ...] = inject_all()


class InvalidMapAnnotationConsumer:
    dependencies: list[CollectionDependency] = inject_map("key")


class InvalidMapKeyTypeConsumer:
    dependencies: dict[int, CollectionDependency] = inject_map("key")


class FactoryRegisteredCollectionDependency(CollectionDependency):
    def __init__(self):
        super().__init__(name="factory-registered", key="factory-registered")


class FactoryRuntimeNonCollection:
    def __init__(self):
        self.name = "factory-runtime-non-collection"
        self.key = "factory-runtime-non-collection"


class FactoryManagedCollectionDependencyFactory(InterfaceFactory[FactoryRegisteredCollectionDependency]):
    def get_object(self, obj: FactoryRegisteredCollectionDependency | None) -> FactoryRegisteredCollectionDependency:
        return FactoryRuntimeNonCollection()  # type: ignore[return-value]


def test_property_injection_uses_unique_compatible_external_object():
    external = ExactPropertyDependency()
    factory = AbstractAutowireCapableFactory(external_objects=[external])
    factory.object_definitions = {
        PropertyTarget: ObjectDefinition(class_object=PropertyTarget),
    }

    created = factory.create_object(PropertyTarget)

    assert isinstance(created, PropertyTarget)
    assert created.dependency is external


def test_property_injection_raises_for_ambiguous_compatible_resources():
    factory = AbstractAutowireCapableFactory(
        external_objects=[ExactPropertyDependency(), AlternatePropertyDependency()]
    )
    factory.object_definitions = {
        PropertyTarget: ObjectDefinition(class_object=PropertyTarget),
    }

    with pytest.raises(AmbiguousDependencyException) as exc_info:
        factory.create_object(PropertyTarget)

    assert "dependency" in str(exc_info.value)
    assert PropertyDependency.__name__ in str(exc_info.value)


def test_after_inject_runs_after_property_injection():
    external = ExactPropertyDependency()
    factory = AbstractAutowireCapableFactory(external_objects=[external])
    factory.object_definitions = {
        PropertyTarget: ObjectDefinition(class_object=PropertyTarget),
    }

    created = factory.create_object(PropertyTarget)

    assert created.observed_dependency is external


def test_subclass_non_marker_override_suppresses_inherited_inject_marker():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        OverrideSuppressesInjectedPropertyTarget: ObjectDefinition(
            class_object=OverrideSuppressesInjectedPropertyTarget
        ),
    }

    created = factory.create_object(OverrideSuppressesInjectedPropertyTarget)

    assert created.dependency is None


def test_property_injection_ignores_unrelated_unresolved_forward_reference_annotations():
    external = ExactPropertyDependency()
    factory = AbstractAutowireCapableFactory(external_objects=[external])
    factory.object_definitions = {
        NarrowAnnotationPropertyTarget: ObjectDefinition(class_object=NarrowAnnotationPropertyTarget),
    }

    created = factory.create_object(NarrowAnnotationPropertyTarget)

    assert created.dependency is external


def test_inherited_inject_marker_uses_subclass_narrowed_annotation():
    exact = ExactPropertyDependency()
    factory = AbstractAutowireCapableFactory(external_objects=[exact, AlternatePropertyDependency()])
    factory.object_definitions = {
        InheritedMarkerNarrowTarget: ObjectDefinition(class_object=InheritedMarkerNarrowTarget),
    }

    created = factory.create_object(InheritedMarkerNarrowTarget)

    assert created.dependency is exact


def test_inherited_inject_marker_uses_subclass_widened_annotation_for_successful_resolution():
    alternate = AlternatePropertyDependency()
    factory = AbstractAutowireCapableFactory(external_objects=[alternate])
    factory.object_definitions = {
        InheritedMarkerWideTarget: ObjectDefinition(class_object=InheritedMarkerWideTarget),
    }

    created = factory.create_object(InheritedMarkerWideTarget)

    assert created.dependency is alternate


def test_inherited_inject_marker_uses_subclass_widened_annotation_for_ambiguity_behavior():
    factory = AbstractAutowireCapableFactory(
        external_objects=[ExactPropertyDependency(), AlternatePropertyDependency()]
    )
    factory.object_definitions = {
        InheritedMarkerWideTarget: ObjectDefinition(class_object=InheritedMarkerWideTarget),
    }

    with pytest.raises(AmbiguousDependencyException) as exc_info:
        factory.create_object(InheritedMarkerWideTarget)

    assert "dependency" in str(exc_info.value)
    assert PropertyDependency.__name__ in str(exc_info.value)


def test_inherited_inject_marker_uses_earlier_mixin_annotation_override_in_final_mro():
    exact = ExactPropertyDependency()
    factory = AbstractAutowireCapableFactory(external_objects=[exact, AlternatePropertyDependency()])
    factory.object_definitions = {
        InheritedMarkerMultipleInheritanceTarget: ObjectDefinition(
            class_object=InheritedMarkerMultipleInheritanceTarget
        ),
    }

    created = factory.create_object(InheritedMarkerMultipleInheritanceTarget)

    assert created.dependency is exact


def test_inject_all_collects_compatible_objects_in_stable_source_order():
    singleton = SingletonCollectedDependency(name="singleton", key="singleton")
    external = ExternalCollectedDependency(name="external", key="external")
    factory = AbstractAutowireCapableFactory(external_objects=[external])
    factory.singleton_objects[SingletonCollectedDependency] = singleton
    factory.object_definitions = {
        OrderedCollectionConsumer: ObjectDefinition(class_object=OrderedCollectionConsumer),
        OrderedCollectionPublisher: ObjectDefinition(class_object=OrderedCollectionPublisher),
        RegisteredCollectedDependency: ObjectDefinition(class_object=RegisteredCollectedDependency),
    }

    created = factory.create_object(OrderedCollectionConsumer)

    assert [dependency.name for dependency in created.dependencies] == [
        "singleton",
        "external",
        "published-first",
        "published-second",
        "registered",
    ]


def test_inject_map_builds_keyed_collection_from_all_compatible_sources():
    singleton = SingletonCollectedDependency(name="singleton", key="singleton")
    external = ExternalCollectedDependency(name="external", key="external")
    factory = AbstractAutowireCapableFactory(external_objects=[external])
    factory.singleton_objects[SingletonCollectedDependency] = singleton
    factory.object_definitions = {
        KeyedCollectionConsumer: ObjectDefinition(class_object=KeyedCollectionConsumer),
        OrderedCollectionPublisher: ObjectDefinition(class_object=OrderedCollectionPublisher),
        RegisteredCollectedDependency: ObjectDefinition(class_object=RegisteredCollectedDependency),
    }

    created = factory.create_object(KeyedCollectionConsumer)

    assert list(created.dependencies) == [
        "singleton",
        "external",
        "published-first",
        "published-second",
        "registered",
    ]
    assert [dependency.name for dependency in created.dependencies.values()] == [
        "singleton",
        "external",
        "published-first",
        "published-second",
        "registered",
    ]


def test_inject_map_raises_for_duplicate_keys():
    external = ExternalCollectedDependency(name="external-duplicate", key="duplicate")
    factory = AbstractAutowireCapableFactory(external_objects=[external])
    factory.object_definitions = {
        KeyedCollectionConsumer: ObjectDefinition(class_object=KeyedCollectionConsumer),
        DuplicateKeyCollectionPublisher: ObjectDefinition(class_object=DuplicateKeyCollectionPublisher),
    }

    with pytest.raises(InvalidInjectionConfigurationError) as exc_info:
        factory.create_object(KeyedCollectionConsumer)

    assert "duplicate" in str(exc_info.value)
    assert "key" in str(exc_info.value)


def test_inject_map_raises_when_key_attribute_is_missing():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        KeyedCollectionConsumer: ObjectDefinition(class_object=KeyedCollectionConsumer),
        MissingKeyCollectionPublisher: ObjectDefinition(class_object=MissingKeyCollectionPublisher),
    }

    with pytest.raises(InvalidInjectionConfigurationError) as exc_info:
        factory.create_object(KeyedCollectionConsumer)

    assert "key" in str(exc_info.value)
    assert "MissingKeyCollectedDependency" in str(exc_info.value)


def test_inject_map_raises_when_key_value_is_none():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        KeyedCollectionConsumer: ObjectDefinition(class_object=KeyedCollectionConsumer),
        NoneKeyCollectionPublisher: ObjectDefinition(class_object=NoneKeyCollectionPublisher),
    }

    with pytest.raises(InvalidInjectionConfigurationError) as exc_info:
        factory.create_object(KeyedCollectionConsumer)

    assert "None" in str(exc_info.value)
    assert "key" in str(exc_info.value)


def test_inject_all_rejects_invalid_annotation_shape():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        InvalidAllAnnotationConsumer: ObjectDefinition(class_object=InvalidAllAnnotationConsumer),
    }

    with pytest.raises(InvalidInjectionConfigurationError) as exc_info:
        factory.create_object(InvalidAllAnnotationConsumer)

    assert "list" in str(exc_info.value)


def test_inject_map_rejects_invalid_annotation_shape():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        InvalidMapAnnotationConsumer: ObjectDefinition(class_object=InvalidMapAnnotationConsumer),
    }

    with pytest.raises(InvalidInjectionConfigurationError) as exc_info:
        factory.create_object(InvalidMapAnnotationConsumer)

    assert "dict" in str(exc_info.value)


def test_inject_all_preserves_actual_publication_order_across_mixed_types():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        OrderedCollectionConsumer: ObjectDefinition(class_object=OrderedCollectionConsumer),
        HeterogeneousCollectionPublisher: ObjectDefinition(class_object=HeterogeneousCollectionPublisher),
    }

    created = factory.create_object(OrderedCollectionConsumer)

    assert [dependency.name for dependency in created.dependencies] == [
        "published-first",
        "published-second",
        "published-third",
    ]


def test_inject_all_uses_order_buckets_for_registered_definitions():
    factory = AbstractAutowireCapableFactory()
    early_definition = ObjectDefinition(class_object=EarlyOrderedCollectedDependency)
    late_definition = ObjectDefinition(class_object=LateOrderedCollectedDependency)
    consumer_definition = ObjectDefinition(class_object=OrderedCollectionConsumer)
    factory.order_definitions = {
        20: [late_definition],
        10: [early_definition],
    }
    factory.object_definitions = {
        OrderedCollectionConsumer: consumer_definition,
        LateOrderedCollectedDependency: late_definition,
        EarlyOrderedCollectedDependency: early_definition,
    }

    created = factory.create_object(OrderedCollectionConsumer)

    assert [dependency.name for dependency in created.dependencies] == [
        "registered-early",
        "registered-late",
    ]


def test_inject_map_validates_runtime_key_type_from_annotation():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        InvalidMapKeyTypeConsumer: ObjectDefinition(class_object=InvalidMapKeyTypeConsumer),
        OrderedCollectionPublisher: ObjectDefinition(class_object=OrderedCollectionPublisher),
    }

    with pytest.raises(InvalidInjectionConfigurationError) as exc_info:
        factory.create_object(InvalidMapKeyTypeConsumer)

    assert "int" in str(exc_info.value)
    assert "str" in str(exc_info.value)


def test_inject_all_does_not_discover_subtypes_from_broad_return_annotations_on_demand():
    factory = AbstractAutowireCapableFactory()
    BroadlyAnnotatedSubtypeCollectionPublisher.instantiated = False
    factory.object_definitions = {
        NarrowCollectionConsumer: ObjectDefinition(class_object=NarrowCollectionConsumer),
        BroadlyAnnotatedSubtypeCollectionPublisher: ObjectDefinition(
            class_object=BroadlyAnnotatedSubtypeCollectionPublisher
        ),
    }

    created = factory.create_object(NarrowCollectionConsumer)

    assert created.dependencies == []
    assert BroadlyAnnotatedSubtypeCollectionPublisher.instantiated is False


def test_inject_map_does_not_discover_subtypes_from_broad_return_annotations_on_demand():
    factory = AbstractAutowireCapableFactory()
    BroadlyAnnotatedSubtypeCollectionPublisher.instantiated = False
    factory.object_definitions = {
        NarrowKeyedCollectionConsumer: ObjectDefinition(class_object=NarrowKeyedCollectionConsumer),
        BroadlyAnnotatedSubtypeCollectionPublisher: ObjectDefinition(
            class_object=BroadlyAnnotatedSubtypeCollectionPublisher
        ),
    }

    created = factory.create_object(NarrowKeyedCollectionConsumer)

    assert created.dependencies == {}
    assert BroadlyAnnotatedSubtypeCollectionPublisher.instantiated is False


def test_inject_all_ignores_broken_broad_publisher_annotation_when_consumer_requests_subtype():
    factory = AbstractAutowireCapableFactory()
    BrokenBroadlyAnnotatedSubtypeCollectionPublisher.instantiated = False
    factory.object_definitions = {
        NarrowCollectionConsumer: ObjectDefinition(class_object=NarrowCollectionConsumer),
        BrokenBroadlyAnnotatedSubtypeCollectionPublisher: ObjectDefinition(
            class_object=BrokenBroadlyAnnotatedSubtypeCollectionPublisher
        ),
    }

    created = factory.create_object(NarrowCollectionConsumer)

    assert created.dependencies == []
    assert BrokenBroadlyAnnotatedSubtypeCollectionPublisher.instantiated is False


def test_inject_map_ignores_broken_broad_publisher_annotation_when_consumer_requests_subtype():
    factory = AbstractAutowireCapableFactory()
    BrokenBroadlyAnnotatedSubtypeCollectionPublisher.instantiated = False
    factory.object_definitions = {
        NarrowKeyedCollectionConsumer: ObjectDefinition(class_object=NarrowKeyedCollectionConsumer),
        BrokenBroadlyAnnotatedSubtypeCollectionPublisher: ObjectDefinition(
            class_object=BrokenBroadlyAnnotatedSubtypeCollectionPublisher
        ),
    }

    created = factory.create_object(NarrowKeyedCollectionConsumer)

    assert created.dependencies == {}
    assert BrokenBroadlyAnnotatedSubtypeCollectionPublisher.instantiated is False


def test_inject_all_does_not_instantiate_object_annotated_publishers_for_unrelated_subtype_requests():
    factory = AbstractAutowireCapableFactory()
    TooBroadObjectCollectionPublisher.instantiated = False
    factory.object_definitions = {
        NarrowCollectionConsumer: ObjectDefinition(class_object=NarrowCollectionConsumer),
        TooBroadObjectCollectionPublisher: ObjectDefinition(class_object=TooBroadObjectCollectionPublisher),
    }

    created = factory.create_object(NarrowCollectionConsumer)

    assert created.dependencies == []
    assert TooBroadObjectCollectionPublisher.instantiated is False


def test_inject_all_ignores_unresolved_annotation_name_overlap_false_positive():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        NameOverlapCollectionConsumer: ObjectDefinition(class_object=NameOverlapCollectionConsumer),
        BrokenNameOverlapCollectionPublisher: ObjectDefinition(class_object=BrokenNameOverlapCollectionPublisher),
    }

    created = factory.create_object(NameOverlapCollectionConsumer)

    assert created.dependencies == []


def test_inject_all_filters_factory_managed_instances_by_runtime_type():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        OrderedCollectionConsumer: ObjectDefinition(class_object=OrderedCollectionConsumer),
        FactoryRegisteredCollectionDependency: ObjectDefinition(class_object=FactoryRegisteredCollectionDependency),
        FactoryManagedCollectionDependencyFactory: ObjectDefinition(
            class_object=FactoryManagedCollectionDependencyFactory,
            is_factory=True,
        ),
    }

    created = factory.create_object(OrderedCollectionConsumer)

    assert created.dependencies == []
    assert isinstance(factory.singleton_objects[FactoryRegisteredCollectionDependency], FactoryRuntimeNonCollection)


def test_inject_map_filters_factory_managed_instances_by_runtime_type():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        KeyedCollectionConsumer: ObjectDefinition(class_object=KeyedCollectionConsumer),
        FactoryRegisteredCollectionDependency: ObjectDefinition(class_object=FactoryRegisteredCollectionDependency),
        FactoryManagedCollectionDependencyFactory: ObjectDefinition(
            class_object=FactoryManagedCollectionDependencyFactory,
            is_factory=True,
        ),
    }

    created = factory.create_object(KeyedCollectionConsumer)

    assert created.dependencies == {}
    assert isinstance(factory.singleton_objects[FactoryRegisteredCollectionDependency], FactoryRuntimeNonCollection)
