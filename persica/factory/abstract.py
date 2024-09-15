import inspect
import logging
from typing import Dict, Generic, Iterable, Optional, Set, Type, TypeVar

from persica.error import NoSuchParameterException
from persica.factory.interface import InterfaceFactory
from persica.scanner.definition import ObjectDefinition

logger = logging.Logger("persica")


class _NoneInstantiate:
    pass


NoneInstantiate = _NoneInstantiate


class AbstractAutowireCapableFactory:
    resolvable_objects: Dict[Type[object], object] = []

    object_map: Dict[Type[object], ObjectDefinition] = {}
    # 实例化的类型
    singleton_objects: Dict[Type[object], object] = {}
    # 实例化的工厂
    singleton_factory: Dict[Type[InterfaceFactory], InterfaceFactory] = {}

    def __init__(self, resolvable_objects: Optional[Iterable[object]] = None):
        if resolvable_objects is not None:
            for k in resolvable_objects:
                original_class: "Type[object]" = k.__class__
                self.resolvable_objects[original_class] = k

    def load(self):
        pass



    def initialize_components(self, component_object: Type[object]) -> object:
        logger.debug("init component %s", component_object.__name__)
        params = {}
        try:
            signature = inspect.signature(component_object.__init__)
        except ValueError as exc:
            print(f"Module {component_object.__name__} get initialize signature error")
            raise exc
        for name, parameter in signature.parameters.items():
            if name in ("self", "args", "kwargs"):
                continue
            if parameter.default != inspect.Parameter.empty:
                params[name] = parameter.default
            else:
                params[name] = None
        for name, parameter in signature.parameters.items():
            if name in ("self", "args", "kwargs"):
                continue
            annotation = parameter.annotation
            instantiate = self.singleton_objects.get(parameter.annotation)
            if instantiate is None:
                instantiate = self.resolvable_objects.get(parameter.annotation)
            if instantiate is None:
                raise NoSuchParameterException(
                    f"Cannot find the {name} parameter of type {annotation.__name__} required "
                    f"by the {component_object.__name__} component"
                )
            if instantiate == NoneInstantiate:
                instantiate = self.initialize_components(parameter.annotation)
            params[name] = instantiate
        component_instantiate = component_object(**params)
        self.singleton_objects[component_object] = component_instantiate
        return component_instantiate

    @staticmethod
    def is_interface_factory(obj: Type[object]) -> bool:
        return issubclass(obj, InterfaceFactory)
