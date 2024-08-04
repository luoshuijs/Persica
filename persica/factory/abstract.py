import inspect
import logging
from typing import Dict, Optional, Iterable, Type, Iterator, Generic, TypeVar, List, Set

from persica.error import NoSuchParameterException
from persica.factory.interface import InterfaceFactory

logger = logging.Logger("persica")

T = TypeVar("T", bound=object)


class _NoneInstantiate:
    pass


NoneInstantiate = _NoneInstantiate


class AbstractAutowireCapableFactory(Generic[T]):
    obj_set: Set[Type[object]] = {}
    # 实例化的类型
    singleton_objects: Dict[Type[object], object] = {}
    # 实例化的工厂
    singleton_factory: Dict[Type[InterfaceFactory], InterfaceFactory] = {}
    # 附加类型
    kwargs: Dict[Type[object], object] = {}

    def __init__(self, kwargs: Optional[Iterable[object]] = None):
        self.kwargs: Dict[Type[object], object] = {}
        if kwargs is not None:
            for k in kwargs:
                original_class: "Type[object]" = k.__class__
                self.kwargs[original_class] = k

    def initialize(self):


        for obj_set in self.obj_set:
            if self.is_interface_factory(obj_set):
                pass

    def initialize_components(self, component_object: Type[T]) -> T:
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
                instantiate = self.kwargs.get(parameter.annotation)
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
