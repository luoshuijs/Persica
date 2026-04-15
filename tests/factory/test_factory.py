import pytest

from persica.error import NoSuchParameterException
from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory


class SimpleClass:
    def __init__(self):
        self.value = "simple"


class DependencyClass:
    def __init__(self):
        self.value = "dependency"


class DependentClass:
    def __init__(self, dependency: DependencyClass):
        self.dependency = dependency


class Product:
    def __init__(self):
        self.name = "Product"


class ProductFactory(InterfaceFactory[Product]):
    def get_object(self, obj: Product | None) -> Product:
        obj.name = "Product from Factory"
        return obj


class ReplacementProductFactory(InterfaceFactory[Product]):
    def get_object(self, obj: Product | None) -> Product:
        replacement = Product()
        replacement.name = "Replacement Product"
        return replacement


class DerivedProductFactory(ProductFactory):
    pass


class NeedsProductFactory:
    def __init__(self, factory: ProductFactory):
        self.factory = factory


class UnresolvedClass:
    def __init__(self, missing_dependency):
        self.missing_dependency = missing_dependency


class TestAbstractAutowireCapableFactory:
    def test_simple_class_instantiation(self):
        factory = AbstractAutowireCapableFactory()
        factory.object_definitions = {SimpleClass: ObjectDefinition(class_object=SimpleClass)}
        factory.instantiate_all_objects()
        instance = factory.singleton_objects.get(SimpleClass)
        assert instance is not None
        assert isinstance(instance, SimpleClass)
        assert instance.value == "simple"

    def test_constructor_injection(self):
        factory = AbstractAutowireCapableFactory()
        factory.object_definitions = {
            DependencyClass: ObjectDefinition(class_object=DependencyClass),
            DependentClass: ObjectDefinition(class_object=DependentClass),
        }
        factory.instantiate_all_objects()
        instance = factory.singleton_objects.get(DependentClass)
        assert instance is not None
        assert isinstance(instance, DependentClass)
        assert instance.dependency is not None
        assert isinstance(instance.dependency, DependencyClass)
        assert instance.dependency.value == "dependency"

    def test_factory_usage(self):
        factory = AbstractAutowireCapableFactory()
        factory.object_definitions = {
            ProductFactory: ObjectDefinition(class_object=ProductFactory, is_factory=True),
            Product: ObjectDefinition(class_object=Product),
        }
        factory.instantiate_all_objects()
        product_instance = factory.singleton_objects.get(Product)
        assert product_instance is not None
        assert isinstance(product_instance, Product)
        assert product_instance.name == "Product from Factory"

    def test_factory_definitions_are_singleton_cached(self):
        factory = AbstractAutowireCapableFactory()
        factory.object_definitions = {
            ProductFactory: ObjectDefinition(class_object=ProductFactory, is_factory=True),
        }

        instance1 = factory.get_object(ProductFactory)
        instance2 = factory.get_object(ProductFactory)

        assert instance1 is not None
        assert instance1 is instance2
        assert factory.singleton_factories.get(ProductFactory) is instance1

    def test_factory_annotation_uses_cached_factory_singleton(self):
        factory = AbstractAutowireCapableFactory()
        cached_factory = ProductFactory()
        factory.object_definitions = {
            ProductFactory: ObjectDefinition(class_object=ProductFactory, is_factory=True),
            NeedsProductFactory: ObjectDefinition(class_object=NeedsProductFactory),
        }
        factory.singleton_factories[ProductFactory] = cached_factory

        instance = factory.create_object(NeedsProductFactory)

        assert isinstance(instance, NeedsProductFactory)
        assert instance.factory is cached_factory
        assert factory.singleton_factories[ProductFactory] is cached_factory

    def test_compatible_factory_annotation_uses_cached_subclass_factory_singleton(self):
        factory = AbstractAutowireCapableFactory()
        cached_factory = DerivedProductFactory()
        factory.object_definitions = {
            DerivedProductFactory: ObjectDefinition(class_object=DerivedProductFactory, is_factory=True),
            NeedsProductFactory: ObjectDefinition(class_object=NeedsProductFactory),
        }
        factory.singleton_factories[DerivedProductFactory] = cached_factory

        instance = factory.create_object(NeedsProductFactory)

        assert isinstance(instance, NeedsProductFactory)
        assert instance.factory is cached_factory
        assert factory.singleton_factories[DerivedProductFactory] is cached_factory

    def test_factory_replacement_instance_is_cached_as_singleton(self):
        factory = AbstractAutowireCapableFactory()
        factory.object_definitions = {
            ReplacementProductFactory: ObjectDefinition(class_object=ReplacementProductFactory, is_factory=True),
            Product: ObjectDefinition(class_object=Product),
        }

        created = factory.create_object(Product)
        cached = factory.singleton_objects.get(Product)
        fetched = factory.get_object(Product)

        assert created is not None
        assert cached is created
        assert fetched is created
        assert created.name == "Replacement Product"

    def test_singleton_behavior(self):
        factory = AbstractAutowireCapableFactory()
        factory.object_definitions = {SimpleClass: ObjectDefinition(class_object=SimpleClass)}
        factory.instantiate_all_objects()
        instance1 = factory.singleton_objects.get(SimpleClass)
        instance2 = factory.get_object(SimpleClass)
        assert instance1 is instance2

    def test_missing_dependency(self):
        factory = AbstractAutowireCapableFactory()
        factory.object_definitions = {UnresolvedClass: ObjectDefinition(class_object=UnresolvedClass)}
        with pytest.raises(NoSuchParameterException) as exc_info:
            factory.instantiate_all_objects()
        assert "Cannot find the missing_dependency" in str(exc_info.value)
