from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.factory.component import BaseComponent
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory


class DefinitionRegistry:
    def __init__(self, factory: "AbstractAutowireCapableFactory"):
        self.factory = factory

    def flash(self):
        for obj in object.__subclasses__():
            if issubclass(obj, BaseComponent):
                self.factory.object_definition_map.setdefault(obj, ObjectDefinition(obj))
            if issubclass(obj, InterfaceFactory):
                self.factory.object_definition_map.setdefault(obj, ObjectDefinition(obj, True))
