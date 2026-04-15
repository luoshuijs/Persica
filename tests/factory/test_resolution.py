import pytest

from persica.error import AmbiguousDependencyException, NoSuchParameterException
from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory


class BaseDependency:
    pass


class SingletonDependency(BaseDependency):
    pass


class ExternalDependency(BaseDependency):
    pass


class RegisteredDependency(BaseDependency):
    pass


class AlternateRegisteredDependency(BaseDependency):
    pass


class NeedsBaseDependency:
    def __init__(self, dependency: BaseDependency):
        self.dependency = dependency


class NeedsDependencyWithDefault:
    def __init__(self, dependency: BaseDependency = "fallback"):
        self.dependency = dependency


class ResolutionProduct:
    def __init__(self):
        self.name = "original"


class ResolutionProductChild(ResolutionProduct):
    pass


class ResolutionProductGrandChild(ResolutionProductChild):
    pass


class CompatibleResolutionFactory(InterfaceFactory[ResolutionProduct]):
    def get_object(self, obj: ResolutionProduct | None) -> ResolutionProduct:
        if obj is not None:
            obj.name = "compatible"
            return obj
        created = ResolutionProduct()
        created.name = "compatible"
        return created


class ExactResolutionFactory(InterfaceFactory[ResolutionProductChild]):
    def get_object(self, obj: ResolutionProductChild | None) -> ResolutionProductChild:
        if obj is not None:
            obj.name = "exact"
            return obj
        created = ResolutionProductChild()
        created.name = "exact"
        return created


class AlternateCompatibleResolutionFactory(InterfaceFactory[ResolutionProductChild]):
    def get_object(self, obj: ResolutionProductChild | None) -> ResolutionProductChild:
        if obj is not None:
            obj.name = "alternate-compatible"
            return obj
        created = ResolutionProductChild()
        created.name = "alternate-compatible"
        return created


class ReplacementResolutionFactory(InterfaceFactory[ResolutionProduct]):
    def get_object(self, obj: ResolutionProduct | None) -> ResolutionProduct:
        replacement = ResolutionProduct()
        replacement.name = "replacement"
        return replacement


class NeedsCompatibleFactory:
    def __init__(self, factory: CompatibleResolutionFactory):
        self.factory = factory


def test_unique_compatible_singleton_dependency_is_injected():
    factory = AbstractAutowireCapableFactory()
    singleton = SingletonDependency()
    factory.singleton_objects[SingletonDependency] = singleton

    resolved = factory._build_constructor_params(NeedsBaseDependency)

    assert resolved["dependency"] is singleton


def test_unique_compatible_external_dependency_is_injected():
    external = ExternalDependency()
    factory = AbstractAutowireCapableFactory(external_objects=[external])

    resolved = factory._build_constructor_params(NeedsBaseDependency)

    assert resolved["dependency"] is external


def test_unique_compatible_registered_definition_is_created_and_injected():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        RegisteredDependency: ObjectDefinition(class_object=RegisteredDependency),
    }

    resolved = factory._build_constructor_params(NeedsBaseDependency)

    assert isinstance(resolved["dependency"], RegisteredDependency)
    assert factory.singleton_objects[RegisteredDependency] is resolved["dependency"]


def test_ambiguous_compatible_dependencies_raise_exception():
    factory = AbstractAutowireCapableFactory()
    factory.singleton_objects[SingletonDependency] = SingletonDependency()
    factory.external_objects[ExternalDependency] = ExternalDependency()

    with pytest.raises(AmbiguousDependencyException) as exc_info:
        factory._build_constructor_params(NeedsBaseDependency)

    assert "dependency" in str(exc_info.value)
    assert BaseDependency.__name__ in str(exc_info.value)


def test_default_parameter_value_is_used_when_dependency_is_missing():
    factory = AbstractAutowireCapableFactory()

    resolved = factory._build_constructor_params(NeedsDependencyWithDefault)

    assert resolved["dependency"] == "fallback"


def test_missing_dependency_without_default_still_raises():
    factory = AbstractAutowireCapableFactory()

    with pytest.raises(NoSuchParameterException):
        factory._build_constructor_params(NeedsBaseDependency)


def test_exact_factory_target_match_is_preferred_over_compatible_match():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ExactResolutionFactory: ObjectDefinition(class_object=ExactResolutionFactory, is_factory=True),
        CompatibleResolutionFactory: ObjectDefinition(class_object=CompatibleResolutionFactory, is_factory=True),
        ResolutionProductChild: ObjectDefinition(class_object=ResolutionProductChild),
    }

    created = factory.create_object(ResolutionProductChild)

    assert created.name == "exact"
    assert factory.singleton_objects[ResolutionProductChild] is created


def test_direct_factory_definitions_are_singleton_cached():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ExactResolutionFactory: ObjectDefinition(class_object=ExactResolutionFactory, is_factory=True),
    }

    first = factory.get_object(ExactResolutionFactory)
    second = factory.get_object(ExactResolutionFactory)

    assert first is second
    assert factory.singleton_factories[ExactResolutionFactory] is first


def test_replacement_instance_from_factory_is_cached_as_singleton():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        ReplacementResolutionFactory: ObjectDefinition(class_object=ReplacementResolutionFactory, is_factory=True),
        ResolutionProduct: ObjectDefinition(class_object=ResolutionProduct),
    }

    created = factory.create_object(ResolutionProduct)
    fetched = factory.get_object(ResolutionProduct)

    assert created is fetched
    assert created.name == "replacement"
    assert factory.singleton_objects[ResolutionProduct] is created


def test_compatible_factory_annotation_uses_cached_factory_singleton():
    factory = AbstractAutowireCapableFactory()
    cached_factory = CompatibleResolutionFactory()
    factory.object_definitions = {
        CompatibleResolutionFactory: ObjectDefinition(class_object=CompatibleResolutionFactory, is_factory=True),
        NeedsCompatibleFactory: ObjectDefinition(class_object=NeedsCompatibleFactory),
    }
    factory.singleton_factories[CompatibleResolutionFactory] = cached_factory

    created = factory.create_object(NeedsCompatibleFactory)

    assert isinstance(created, NeedsCompatibleFactory)
    assert created.factory is cached_factory


def test_ambiguous_compatible_factories_raise_exception():
    factory = AbstractAutowireCapableFactory()
    factory.object_definitions = {
        CompatibleResolutionFactory: ObjectDefinition(class_object=CompatibleResolutionFactory, is_factory=True),
        AlternateCompatibleResolutionFactory: ObjectDefinition(
            class_object=AlternateCompatibleResolutionFactory,
            is_factory=True,
        ),
        ResolutionProductGrandChild: ObjectDefinition(class_object=ResolutionProductGrandChild),
    }

    with pytest.raises(AmbiguousDependencyException) as exc_info:
        factory.create_object(ResolutionProductGrandChild)

    assert ResolutionProductGrandChild.__name__ in str(exc_info.value)
