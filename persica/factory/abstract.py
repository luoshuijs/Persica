import inspect
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, cast

from persica.error import NoSuchParameterException
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory
from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from logging import Logger

_LOGGER = get_logger(__name__, "AbstractAutowireCapableFactory")


class AbstractAutowireCapableFactory:
    _logger: "Logger" = _LOGGER
    # 存储对象定义的映射表，key 为对象的类，value 为 ObjectDefinition
    object_definitions: dict[type[object], ObjectDefinition] = {}
    # 工厂缓存，缓存已经创建的工厂对象，key 为对象的类，value 为工厂实例
    factory_cache: dict[type[object], InterfaceFactory] = {}
    # 存储已经实例化的单例对象，key 为对象的类，value 为对象实例
    singleton_objects: dict[type[object], object] = {}
    # 存储已经实例化的工厂对象，key 为工厂类，value 为工厂实例
    singleton_factories: dict[type[InterfaceFactory], InterfaceFactory] = {}
    # 存储外部可注入的对象，key 为对象的类，value 为对象实例
    external_objects: dict[type[object], object] = {}

    def __init__(self, external_objects: Iterable[object] | None = None):
        """
        初始化工厂，允许外部传入可解析的对象，并将它们存入 external_objects。
        """
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
        for definition in self.object_definitions.values():
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
            cls = cast(type[InterfaceFactory], cls)
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
                self.singleton_objects[cls] = obj
                return instance
        # 如果没有工厂管理，直接返回对象
        self.singleton_objects[cls] = obj
        return obj

    def _find_factory_for_class(self, cls: type[object]) -> InterfaceFactory | None:
        """
        查找与给定类对应的工厂，如果没有找到则返回 None。
        """
        # 先检查工厂缓存中是否存在
        factory = self.factory_cache.get(cls)
        if factory is None:
            # 遍历 object_definitions 查找是否有与该类对应的工厂
            for key, definition in self.object_definitions.items():
                if definition.is_factory:
                    factory_cls = cast(type[InterfaceFactory], key)
                    # 判断该类是否是工厂管理的类或其子类
                    if issubclass(cls, factory_cls.get_class()):
                        factory_instance = self.singleton_factories.get(factory_cls)
                        if factory_instance is None:
                            factory_instance = self.create_object(factory_cls)
                            factory = cast(InterfaceFactory, factory_instance)
                        else:
                            factory = factory_instance
                        # 缓存工厂实例
                        self.factory_cache[cls] = factory
                        self.singleton_factories[factory_cls] = factory
                        break
        return factory

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
            # 跳过 'self', 'args', 'kwargs'
            if name in ("self", "args", "kwargs"):
                continue
            annotation = parameter.annotation
            # 从单例缓存或外部对象中获取依赖对象实例
            instance = self.singleton_objects.get(annotation) or self.external_objects.get(annotation)
            # 如果没有找到依赖对象，尝试创建
            if instance is None:
                object_definition = self.object_definitions.get(annotation)
                if object_definition is not None:
                    instance = self.create_object(object_definition.class_object)
                    self.singleton_objects[object_definition.class_object] = instance
            # 如果依然没有找到，检查参数是否有默认值
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
