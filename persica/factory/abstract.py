import inspect
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, cast

from persica.error import AmbiguousDependencyException, NoSuchParameterException
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory
from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from logging import Logger

_LOGGER = get_logger(__name__, "AbstractAutowireCapableFactory")


class AbstractAutowireCapableFactory:
    _logger: "Logger" = _LOGGER
    # 存储对象定义对应的加载顺序的映射表，key 为顺序，value 为 ObjectDefinition
    order_definitions: dict[int, list[ObjectDefinition]]
    # 存储对象定义的映射表，key 为对象的类，value 为 ObjectDefinition
    object_definitions: dict[type[object], ObjectDefinition]
    # 工厂缓存，缓存已经创建的工厂对象，key 为对象的类，value 为工厂实例
    factory_cache: dict[type[object], InterfaceFactory]
    # 存储已经实例化的单例对象，key 为对象的类，value 为对象实例
    singleton_objects: dict[type[object], object]
    # 存储已经实例化的工厂对象，key 为工厂类，value 为工厂实例
    singleton_factories: dict[type[InterfaceFactory], InterfaceFactory]
    # 存储外部可注入的对象，key 为对象的类，value 为对象实例
    external_objects: dict[type[object], object]

    def __init__(self, external_objects: Iterable[object] | None = None):
        """
        初始化工厂，允许外部传入可解析的对象，并将它们存入 external_objects。
        """
        self.order_definitions = {}
        self.object_definitions = {}
        self.factory_cache = {}
        self.singleton_objects = {}
        self.singleton_factories = {}
        self.external_objects = {}

        if external_objects is not None:
            for obj in external_objects:
                original_class = obj.__class__
                self.external_objects.setdefault(original_class, obj)

    def add_external_object(self, external_objects: object):
        original_class = external_objects.__class__
        self.external_objects.setdefault(original_class, external_objects)

    def instantiate_all_objects(self):
        """
        实例化 object_definitions 中所有的对象。
        """
        self._logger.info("Instantiating all objects")
        ordered_classes: set[type[object]] = set()
        sorted_definition = sorted(self.order_definitions.items())
        for _, definitions in sorted_definition:
            for definition in definitions:
                ordered_classes.add(definition.class_object)
                self.get_object(definition.class_object)
        for definition in self.object_definitions.values():
            if definition.class_object in ordered_classes:
                continue
            self.get_object(definition.class_object)

    def get_object(self, cls: type[object]):
        """
        根据类获取对象实例，如果未创建则调用 create_object 方法创建。
        """
        definition = self.object_definitions.get(cls)
        if definition is None:
            self._logger.warning("No definition found for class %s", cls.__name__)
            return None

        if definition.is_factory:
            # 如果对象定义是工厂，则获取或创建工厂对象
            cls = cast("type[InterfaceFactory]", cls)
            obj = self.singleton_factories.get(cls)
            if obj is None:
                return self.create_object(cls)
        else:
            # 如果对象定义不是工厂，则获取或创建单例对象
            obj = self.singleton_objects.get(cls)
            if obj is None:
                return self.create_object(cls)
        return obj

    def create_object(self, cls: type[object]) -> object:
        """
        创建一个对象实例，支持依赖注入和工厂管理。
        """
        self._logger.info("Creating object %s", cls.__name__)
        definition = self.object_definitions.get(cls)
        # 查找是否有该类的工厂
        factory = self._find_factory_for_class(cls)
        # 构建构造函数参数
        params = self._build_constructor_params(cls)
        # 创建对象
        obj = cls(**params)
        # 如果该类有工厂管理，则通过工厂获取实例
        if factory is not None:
            instance = factory.get_object(obj)
            if instance is not None:
                self.singleton_objects[cls] = instance
                return instance
        # 如果没有工厂管理，直接返回对象
        if definition is not None and definition.is_factory:
            self.singleton_factories[cast("type[InterfaceFactory]", cls)] = cast("InterfaceFactory", obj)
            return obj
        self.singleton_objects[cls] = obj
        return obj

    def _find_factory_for_class(self, cls: type[object]) -> InterfaceFactory | None:
        """
        查找与给定类对应的工厂，如果没有找到则返回 None。
        """
        factory = self.factory_cache.get(cls)
        if factory is not None:
            return factory

        exact_matches: list[type[InterfaceFactory]] = []
        compatible_matches: list[type[InterfaceFactory]] = []
        for key, definition in self.object_definitions.items():
            if not definition.is_factory:
                continue
            factory_cls = cast("type[InterfaceFactory]", key)
            target_class = factory_cls.get_class()
            if target_class == cls:
                exact_matches.append(factory_cls)
                continue
            if issubclass(cls, target_class):
                compatible_matches.append(factory_cls)

        selected_factory_cls: type[InterfaceFactory] | None = None
        if len(exact_matches) == 1:
            selected_factory_cls = exact_matches[0]
        elif len(exact_matches) > 1:
            raise AmbiguousDependencyException(f"Multiple factories exactly match the {cls.__name__} product")
        elif len(compatible_matches) == 1:
            selected_factory_cls = compatible_matches[0]
        elif len(compatible_matches) > 1:
            raise AmbiguousDependencyException(f"Multiple compatible factories found for the {cls.__name__} product")

        if selected_factory_cls is None:
            return None

        factory_instance = self.singleton_factories.get(selected_factory_cls)
        if factory_instance is None:
            factory_instance = cast("InterfaceFactory", self.create_object(selected_factory_cls))

        self.factory_cache[cls] = factory_instance
        self.singleton_factories[selected_factory_cls] = factory_instance
        return factory_instance

    def _build_constructor_params(self, cls: type[object]) -> dict[str, Any]:
        """
        构建构造函数参数，支持依赖注入和默认值处理。
        """
        try:
            # 获取构造函数签名，并设置 eval_str=True 以支持 Python 3.10+ 的字符串注解
            signature = inspect.signature(cls.__init__, eval_str=True)
        except ValueError as exc:
            self._logger.exception("Failed to retrieve __init__ signature for %s: %s", cls.__name__, exc_info=exc)
            raise

        params: dict[str, Any] = {}
        for name, parameter in signature.parameters.items():
            if name in ("self", "args", "kwargs"):
                continue
            annotation = parameter.annotation
            instance = self._resolve_dependency(annotation, name)
            if instance is None:
                if parameter.default != inspect.Parameter.empty:
                    instance = parameter.default
                else:
                    raise NoSuchParameterException(
                        f"Cannot find the {name} parameter of type {annotation.__name__} required "
                        f"by the {cls.__name__} component"
                    )
            params[name] = instance
        return params

    def _resolve_dependency(self, annotation: Any, parameter_name: str) -> object | None:  # noqa: PLR0911, PLR0912
        if not isinstance(annotation, type):
            return None

        exact_singleton = self.singleton_objects.get(annotation)
        if exact_singleton is not None:
            return exact_singleton

        exact_external = self.external_objects.get(annotation)
        if exact_external is not None:
            return exact_external

        exact_definition = self.object_definitions.get(annotation)
        if exact_definition is not None:
            return self.get_object(exact_definition.class_object)

        compatible_candidates: dict[type[object], tuple[str, object | ObjectDefinition]] = {}
        for candidate_cls, instance in self.singleton_objects.items():
            if issubclass(candidate_cls, annotation):
                compatible_candidates[candidate_cls] = ("singleton", instance)
        for candidate_cls, instance in self.external_objects.items():
            if issubclass(candidate_cls, annotation) and candidate_cls not in compatible_candidates:
                compatible_candidates[candidate_cls] = ("external", instance)
        for candidate_cls, definition in self.object_definitions.items():
            if issubclass(candidate_cls, annotation) and candidate_cls not in compatible_candidates:
                compatible_candidates[candidate_cls] = ("definition", definition)

        if len(compatible_candidates) > 1:
            raise AmbiguousDependencyException(
                f"Multiple compatible dependencies found for parameter {parameter_name} of type "
                f"{annotation.__name__}: {', '.join(candidate_cls.__name__ for candidate_cls in compatible_candidates)}"
            )
        if not compatible_candidates:
            return None

        _, (source, value) = next(iter(compatible_candidates.items()))
        if source == "definition":
            definition = cast("ObjectDefinition", value)
            return self.get_object(definition.class_object)
        return cast("object", value)
