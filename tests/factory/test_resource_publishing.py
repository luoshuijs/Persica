import pytest

from persica import inject
from persica.error import AmbiguousDependencyException, InvalidInjectionConfigurationError, NoSuchParameterException
from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory


class PublishedBaseResource:
    pass


class PublishedResource(PublishedBaseResource):
    pass


class RegisteredPublishedResource(PublishedResource):
    pass


class DefinedPublishedResource:
    pass


class CompatibleRegisteredResource(PublishedBaseResource):
    pass


class ResourcePublishingComponent:
    def __init__(self):
        self.published = PublishedResource()
        self.after_inject_dependency = None

    def provide_objects(self) -> list[PublishedResource]:
        return [self.published]

    def after_inject(self):
        self.after_inject_dependency = self.published


class BroadlyAnnotatedPublishingComponent:
    instantiated = False

    def __init__(self):
        type(self).instantiated = True
        self.published = PublishedResource()

    def provide_objects(self) -> list[PublishedBaseResource]:
        return [self.published]


class TooBroadObjectPublishingComponent:
    instantiated = False

    def __init__(self):
        type(self).instantiated = True
        self.published = object()

    def provide_objects(self) -> list[object]:
        return [self.published]


class FactoryManagedDependency:
    pass


class FactoryManagedPublishedResource:
    pass


class ReplacementPublishedProduct:
    pass


class FactoryManagedPublishedComponent:
    dependency: FactoryManagedDependency = inject()

    def __init__(self):
        self.published = FactoryManagedPublishedResource()
        self.after_inject_dependency = None

    def provide_objects(self) -> list[FactoryManagedPublishedResource]:
        return [self.published]

    def after_inject(self):
        self.after_inject_dependency = self.dependency


class FactoryManagedPublishedComponentFactory(InterfaceFactory[FactoryManagedPublishedComponent]):
    source: FactoryManagedPublishedComponent | None = None

    @classmethod
    def get_class(cls):
        return FactoryManagedPublishedComponent

    def get_object(
        self, obj: FactoryManagedPublishedComponent | None
    ) -> FactoryManagedPublishedComponent | ReplacementPublishedProduct:
        type(self).source = obj
        return ReplacementPublishedProduct()


class FactoryManagedPublishedResourceConsumer:
    resource: FactoryManagedPublishedResource = inject()


class PublishedResourceConsumer:
    resource: PublishedResource = inject()
    compatible_resource: PublishedBaseResource = inject()


class ExactTypePublishingComponent:
    def __init__(self):
        self.published = DefinedPublishedResource()

    def provide_objects(self) -> list[DefinedPublishedResource]:
        return [self.published]


class DuplicatePublishingComponent:
    def __init__(self):
        self.first = PublishedResource()
        self.second = PublishedResource()

    def provide_objects(self) -> list[PublishedResource]:
        return [self.first, self.second]


class TuplePublishingComponent:
    def __init__(self):
        self.published = PublishedResource()

    def provide_objects(self) -> list[PublishedResource]:
        return (self.published,)


class UnresolvedAnnotatedPublisher:
    def __init__(self):
        self.published = PublishedResource()

    def provide_objects(self):
        return [self.published]


UnresolvedAnnotatedPublisher.provide_objects.__annotations__ = {"return": "DoesNotExist"}


class RelevantBrokenPublishedResourcePublisher:
    def __init__(self):
        self.published = PublishedResource()

    def provide_objects(self):
        return [self.published]


RelevantBrokenPublishedResourcePublisher.provide_objects.__annotations__ = {
    "return": "BrokenContainer[PublishedResource]"
}


class RelevantBrokenBroadPublishedResourcePublisher:
    def __init__(self):
        self.published = PublishedResource()

    def provide_objects(self):
        return [self.published]


RelevantBrokenBroadPublishedResourcePublisher.provide_objects.__annotations__ = {
    "return": "BrokenContainer[PublishedBaseResource]"
}


class CollisionNamespaceA:
    class SharedPublishedResource:
        pass


class CollisionNamespaceB:
    class SharedPublishedResource:
        pass


class CollisionExactPublishedResourceConsumer:
    resource: CollisionNamespaceA.SharedPublishedResource = inject()


class CollisionExactPublishingComponent:
    def __init__(self):
        self.published = CollisionNamespaceA.SharedPublishedResource()

    def provide_objects(self) -> list[CollisionNamespaceA.SharedPublishedResource]:
        return [self.published]


class CollisionBrokenPublishedResourcePublisher:
    def provide_objects(self):
        return []


CollisionBrokenPublishedResourcePublisher.provide_objects.__annotations__ = {
    "return": "BrokenContainer[SharedPublishedResource]"
}


class AfterInjectFailurePublishedResource:
    pass


class FailingAfterInjectPublisher:
    def __init__(self):
        self.published = AfterInjectFailurePublishedResource()

    def provide_objects(self) -> list[AfterInjectFailurePublishedResource]:
        return [self.published]

    def after_inject(self):
        raise RuntimeError("after_inject failed")


class AfterInjectFailureConsumer:
    resource: AfterInjectFailurePublishedResource = inject()


class ClassLocalTypePublishingComponent:
    class LocalPublishedResource:
        pass

    def __init__(self):
        self.published = self.LocalPublishedResource()

    def provide_objects(self):
        return [self.published]


ClassLocalTypePublishingComponent.provide_objects.__annotations__ = {"return": "list[LocalPublishedResource]"}


class ClassLocalTypePublishedResourceConsumer:
    resource: ClassLocalTypePublishingComponent.LocalPublishedResource = inject()


class CompatiblePublishedResourceOnlyConsumer:
    compatible_resource: PublishedBaseResource = inject()


class ConstructorPublishedResourceConsumer:
    def __init__(self, resource: PublishedResource, compatible_resource: PublishedBaseResource):
        self.resource = resource
        self.compatible_resource = compatible_resource


class ExactPublishedResourcePropertyConsumer:
    resource: DefinedPublishedResource = inject()


class ExactPublishedResourceOnlyConsumer:
    resource: PublishedResource = inject()


class ExactPublishedResourceConstructorConsumer:
    def __init__(self, resource: DefinedPublishedResource):
        self.resource = resource


class BrokenDependency:
    pass


class UnrelatedBrokenComponent:
    def __init__(self, dependency: BrokenDependency):
        self.dependency = dependency


def test_published_resources_are_injectable_for_exact_and_compatible_property_injection():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ResourcePublishingComponent: ObjectDefinition(class_object=ResourcePublishingComponent),
        PublishedResourceConsumer: ObjectDefinition(class_object=PublishedResourceConsumer),
    }

    factory.instantiate_all_objects()

    publisher = factory.singleton_objects[ResourcePublishingComponent]
    consumer = factory.singleton_objects[PublishedResourceConsumer]
    assert consumer.resource is publisher.published
    assert consumer.compatible_resource is publisher.published


def test_published_resources_are_injectable_when_publisher_is_registered_after_consumer():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        PublishedResourceConsumer: ObjectDefinition(class_object=PublishedResourceConsumer),
        ResourcePublishingComponent: ObjectDefinition(class_object=ResourcePublishingComponent),
    }

    factory.instantiate_all_objects()

    publisher = factory.singleton_objects[ResourcePublishingComponent]
    consumer = factory.singleton_objects[PublishedResourceConsumer]
    assert consumer.resource is publisher.published
    assert consumer.compatible_resource is publisher.published


def test_exact_published_resource_discovery_ignores_broader_declared_return_types():
    factory = AbstractAutowireCapableFactory()
    BroadlyAnnotatedPublishingComponent.instantiated = False
    factory.object_definitions = {
        ExactPublishedResourceOnlyConsumer: ObjectDefinition(class_object=ExactPublishedResourceOnlyConsumer),
        BroadlyAnnotatedPublishingComponent: ObjectDefinition(class_object=BroadlyAnnotatedPublishingComponent),
    }

    with pytest.raises(NoSuchParameterException) as exc_info:
        factory.create_object(ExactPublishedResourceOnlyConsumer)

    assert BroadlyAnnotatedPublishingComponent.instantiated is False
    assert "PublishedResource" in str(exc_info.value)


def test_exact_published_resource_discovery_ignores_object_annotated_publishers_for_concrete_requests():
    factory = AbstractAutowireCapableFactory()
    TooBroadObjectPublishingComponent.instantiated = False
    factory.object_definitions = {
        ExactPublishedResourceOnlyConsumer: ObjectDefinition(class_object=ExactPublishedResourceOnlyConsumer),
        TooBroadObjectPublishingComponent: ObjectDefinition(class_object=TooBroadObjectPublishingComponent),
    }

    with pytest.raises(NoSuchParameterException) as exc_info:
        factory.create_object(ExactPublishedResourceOnlyConsumer)

    assert TooBroadObjectPublishingComponent.instantiated is False
    assert "PublishedResource" in str(exc_info.value)


def test_property_injection_only_instantiates_matching_publishers_for_missing_resources():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        PublishedResourceConsumer: ObjectDefinition(class_object=PublishedResourceConsumer),
        UnrelatedBrokenComponent: ObjectDefinition(class_object=UnrelatedBrokenComponent),
        ResourcePublishingComponent: ObjectDefinition(class_object=ResourcePublishingComponent),
    }

    created = factory.create_object(PublishedResourceConsumer)

    publisher = factory.singleton_objects[ResourcePublishingComponent]
    assert created.resource is publisher.published
    assert created.compatible_resource is publisher.published
    assert UnrelatedBrokenComponent not in factory.singleton_objects


def test_constructor_injection_uses_published_resources_when_publisher_is_registered_after_consumer():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ConstructorPublishedResourceConsumer: ObjectDefinition(class_object=ConstructorPublishedResourceConsumer),
        UnrelatedBrokenComponent: ObjectDefinition(class_object=UnrelatedBrokenComponent),
        ResourcePublishingComponent: ObjectDefinition(class_object=ResourcePublishingComponent),
    }

    created = factory.create_object(ConstructorPublishedResourceConsumer)

    publisher = factory.singleton_objects[ResourcePublishingComponent]
    assert created.resource is publisher.published
    assert created.compatible_resource is publisher.published
    assert UnrelatedBrokenComponent not in factory.singleton_objects


def test_exact_registered_definition_beats_published_resource_for_property_injection():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ExactPublishedResourcePropertyConsumer: ObjectDefinition(class_object=ExactPublishedResourcePropertyConsumer),
        DefinedPublishedResource: ObjectDefinition(class_object=DefinedPublishedResource),
        ExactTypePublishingComponent: ObjectDefinition(class_object=ExactTypePublishingComponent),
    }

    created = factory.create_object(ExactPublishedResourcePropertyConsumer)

    assert isinstance(created.resource, DefinedPublishedResource)
    assert created.resource is factory.singleton_objects[DefinedPublishedResource]


def test_exact_registered_definition_beats_published_resource_for_constructor_injection():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ExactPublishedResourceConstructorConsumer: ObjectDefinition(
            class_object=ExactPublishedResourceConstructorConsumer
        ),
        DefinedPublishedResource: ObjectDefinition(class_object=DefinedPublishedResource),
        ExactTypePublishingComponent: ObjectDefinition(class_object=ExactTypePublishingComponent),
    }

    created = factory.create_object(ExactPublishedResourceConstructorConsumer)

    assert isinstance(created.resource, DefinedPublishedResource)
    assert created.resource is factory.singleton_objects[DefinedPublishedResource]


def test_compatible_registered_definition_beats_compatible_published_resource():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        PublishedResourceConsumer: ObjectDefinition(class_object=PublishedResourceConsumer),
        CompatibleRegisteredResource: ObjectDefinition(class_object=CompatibleRegisteredResource),
        ResourcePublishingComponent: ObjectDefinition(class_object=ResourcePublishingComponent),
    }

    created = factory.create_object(PublishedResourceConsumer)

    assert isinstance(created.compatible_resource, CompatibleRegisteredResource)
    assert created.compatible_resource is factory.singleton_objects[CompatibleRegisteredResource]


def test_compatible_registered_definition_beats_already_published_compatible_resource():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ResourcePublishingComponent: ObjectDefinition(class_object=ResourcePublishingComponent),
        PublishedResourceConsumer: ObjectDefinition(class_object=PublishedResourceConsumer),
        CompatibleRegisteredResource: ObjectDefinition(class_object=CompatibleRegisteredResource),
    }

    factory.create_object(ResourcePublishingComponent)
    created = factory.create_object(PublishedResourceConsumer)

    assert isinstance(created.compatible_resource, CompatibleRegisteredResource)
    assert created.compatible_resource is factory.singleton_objects[CompatibleRegisteredResource]


def test_after_inject_runs_after_resource_publication():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ResourcePublishingComponent: ObjectDefinition(class_object=ResourcePublishingComponent),
    }

    created = factory.create_object(ResourcePublishingComponent)

    assert created.after_inject_dependency is created.published


def test_published_resources_roll_back_when_after_inject_fails():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        FailingAfterInjectPublisher: ObjectDefinition(class_object=FailingAfterInjectPublisher),
        AfterInjectFailureConsumer: ObjectDefinition(class_object=AfterInjectFailureConsumer),
    }

    with pytest.raises(RuntimeError) as exc_info:
        factory.create_object(FailingAfterInjectPublisher)

    assert "after_inject failed" in str(exc_info.value)
    assert AfterInjectFailurePublishedResource not in factory.published_objects
    assert factory.published_object_sequence == []

    with pytest.raises(RuntimeError) as retry_exc_info:
        factory.create_object(AfterInjectFailureConsumer)

    assert "after_inject failed" in str(retry_exc_info.value)
    assert AfterInjectFailurePublishedResource not in factory.published_objects
    assert factory.published_object_sequence == []


def test_publisher_discovery_resolves_class_local_return_annotation_names():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ClassLocalTypePublishedResourceConsumer: ObjectDefinition(class_object=ClassLocalTypePublishedResourceConsumer),
        ClassLocalTypePublishingComponent: ObjectDefinition(class_object=ClassLocalTypePublishingComponent),
    }

    created = factory.create_object(ClassLocalTypePublishedResourceConsumer)

    publisher = factory.singleton_objects[ClassLocalTypePublishingComponent]
    assert created.resource is publisher.published


def test_factory_replacement_preserves_task2_wiring_on_registered_component_instance():
    factory = AbstractAutowireCapableFactory(external_objects=[FactoryManagedDependency()])
    FactoryManagedPublishedComponentFactory.source = None
    factory.object_definitions = {
        FactoryManagedPublishedComponentFactory: ObjectDefinition(
            class_object=FactoryManagedPublishedComponentFactory,
            is_factory=True,
        ),
        FactoryManagedPublishedComponent: ObjectDefinition(class_object=FactoryManagedPublishedComponent),
        FactoryManagedPublishedResourceConsumer: ObjectDefinition(class_object=FactoryManagedPublishedResourceConsumer),
    }

    created = factory.create_object(FactoryManagedPublishedComponent)
    source = FactoryManagedPublishedComponentFactory.source

    assert isinstance(created, ReplacementPublishedProduct)
    assert factory.singleton_objects[FactoryManagedPublishedComponent] is created
    assert source is not None
    assert isinstance(source.dependency, FactoryManagedDependency)
    assert source.after_inject_dependency is source.dependency

    consumer = factory.create_object(FactoryManagedPublishedResourceConsumer)
    assert consumer.resource is source.published


def test_published_resources_are_not_registered_as_lifecycle_components():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ResourcePublishingComponent: ObjectDefinition(class_object=ResourcePublishingComponent),
        PublishedResourceConsumer: ObjectDefinition(class_object=PublishedResourceConsumer),
    }

    factory.instantiate_all_objects()

    assert PublishedResource not in factory.object_definitions
    assert PublishedResource not in factory.singleton_objects


def test_duplicate_published_resources_of_same_runtime_type_raise_ambiguity():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        DuplicatePublishingComponent: ObjectDefinition(class_object=DuplicatePublishingComponent),
        PublishedResourceConsumer: ObjectDefinition(class_object=PublishedResourceConsumer),
    }

    with pytest.raises(AmbiguousDependencyException) as exc_info:
        factory.instantiate_all_objects()

    assert PublishedResource.__name__ in str(exc_info.value)


def test_provide_objects_requires_list_return_value():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        TuplePublishingComponent: ObjectDefinition(class_object=TuplePublishingComponent),
    }

    with pytest.raises(InvalidInjectionConfigurationError) as exc_info:
        factory.create_object(TuplePublishingComponent)

    assert "must return a list" in str(exc_info.value)


def test_publisher_discovery_ignores_unrelated_unresolved_return_annotation():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        PublishedResourceConsumer: ObjectDefinition(class_object=PublishedResourceConsumer),
        UnresolvedAnnotatedPublisher: ObjectDefinition(class_object=UnresolvedAnnotatedPublisher),
        ResourcePublishingComponent: ObjectDefinition(class_object=ResourcePublishingComponent),
    }

    created = factory.create_object(PublishedResourceConsumer)

    publisher = factory.singleton_objects[ResourcePublishingComponent]
    assert created.resource is publisher.published


def test_relevant_broken_publisher_annotation_raises_configuration_error():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ExactPublishedResourceOnlyConsumer: ObjectDefinition(class_object=ExactPublishedResourceOnlyConsumer),
        RelevantBrokenPublishedResourcePublisher: ObjectDefinition(
            class_object=RelevantBrokenPublishedResourcePublisher
        ),
    }

    with pytest.raises(InvalidInjectionConfigurationError) as exc_info:
        factory.create_object(ExactPublishedResourceOnlyConsumer)

    assert "RelevantBrokenPublishedResourcePublisher.provide_objects() return annotation" in str(exc_info.value)


def test_exact_published_resource_discovery_ignores_broken_broader_return_annotations():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ExactPublishedResourceOnlyConsumer: ObjectDefinition(class_object=ExactPublishedResourceOnlyConsumer),
        RelevantBrokenBroadPublishedResourcePublisher: ObjectDefinition(
            class_object=RelevantBrokenBroadPublishedResourcePublisher
        ),
    }

    with pytest.raises(NoSuchParameterException) as exc_info:
        factory.create_object(ExactPublishedResourceOnlyConsumer)

    assert "PublishedResource" in str(exc_info.value)


def test_compatible_relevant_broken_publisher_annotation_raises_configuration_error():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        CompatiblePublishedResourceOnlyConsumer: ObjectDefinition(class_object=CompatiblePublishedResourceOnlyConsumer),
        RelevantBrokenPublishedResourcePublisher: ObjectDefinition(
            class_object=RelevantBrokenPublishedResourcePublisher
        ),
    }

    with pytest.raises(InvalidInjectionConfigurationError) as exc_info:
        factory.create_object(CompatiblePublishedResourceOnlyConsumer)

    assert "RelevantBrokenPublishedResourcePublisher.provide_objects() return annotation" in str(exc_info.value)


def test_exact_published_resource_discovery_ignores_ambiguous_simple_name_broken_annotations():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        CollisionExactPublishedResourceConsumer: ObjectDefinition(class_object=CollisionExactPublishedResourceConsumer),
        CollisionBrokenPublishedResourcePublisher: ObjectDefinition(
            class_object=CollisionBrokenPublishedResourcePublisher
        ),
        CollisionExactPublishingComponent: ObjectDefinition(class_object=CollisionExactPublishingComponent),
    }

    created = factory.create_object(CollisionExactPublishedResourceConsumer)

    publisher = factory.singleton_objects[CollisionExactPublishingComponent]
    assert created.resource is publisher.published
