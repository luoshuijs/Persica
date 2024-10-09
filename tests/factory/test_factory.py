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

    def test_singleton_behavior(self):
        factory = AbstractAutowireCapableFactory()
        factory.object_definition = {SimpleClass: ObjectDefinition(class_object=SimpleClass)}
        factory.instantiate_all_objects()
        instance1 = factory.singleton_objects.get(SimpleClass)
        instance2 = factory.singleton_objects.get(SimpleClass)
        assert instance1 is instance2

    def test_missing_dependency(self):
        factory = AbstractAutowireCapableFactory()
        factory.object_definitions = {UnresolvedClass: ObjectDefinition(class_object=UnresolvedClass)}
        with pytest.raises(NoSuchParameterException) as exc_info:
            factory.instantiate_all_objects()
        assert "Cannot find the missing_dependency" in str(exc_info.value)
