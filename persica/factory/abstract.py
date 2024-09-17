import inspect
from typing import TYPE_CHECKING, Dict, Iterable, Optional, Type, Union, cast

from persica.error import NoSuchParameterException
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory
from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from logging import Logger

_LOGGER = get_logger(__name__, "AbstractAutowireCapableFactory")


class AbstractAutowireCapableFactory:
    _logger: "Logger" = _LOGGER
    # 相关定义
    object_definition_map: Dict[Type[object], ObjectDefinition] = {}
    # 工厂缓存映射
    factory_object_cache: Dict[Type[object], Union[InterfaceFactory]] = {}
    # 实例化的类型
    singleton_objects: Dict[Type[object], object] = {}
    # 实例化的工厂
    singleton_factory: Dict[Type[InterfaceFactory], InterfaceFactory] = {}
    # 附加类型
    resolvable_objects: Dict[Type[object], object] = []

    def __init__(self, resolvable_objects: Optional[Iterable[object]] = None):
        if resolvable_objects is not None:
            for k in resolvable_objects:
                original_class: "Type[object]" = k.__class__
                self.resolvable_objects[original_class] = k

    def register_object_definition(self, definition: ObjectDefinition) -> None:
        pass

    def instantiate_object(self):
        self._logger.info("Instantiate Object")

        for _, value in self.object_definition_map.items():
            self._get_object(value)

    def _get_object(self, definition: ObjectDefinition):
        class_object = definition.class_object

        if definition.is_factory:
            class_object = cast(Type[InterfaceFactory], class_object)
            obj = self.singleton_factory.get(class_object)
            if obj is None:
                return self._create_object(class_object)
        else:
            obj = self.singleton_objects.get(class_object)
            if obj is None:
                return self._create_object(class_object)

    def _create_object(self, class_object: Type[object]) -> object:
        self._logger.info("create object %s", class_object.__name__)
        # 检查这个 class_object 是否需要指定工厂初始化或者管理
        factory = self.factory_object_cache.get(class_object)
        if factory is None:
            # 遍历 object_definition_nmap 查找是否有对应的工厂
            for key, _object_definition in self.object_definition_map.items():
                # 判断是否为工厂
                if _object_definition.is_factory:
                    key = cast(Type[InterfaceFactory], key)
                    # 判断这个工厂是否为 class_object 的工厂
                    if key.object_to_assemble == class_object:
                        # 如果存在对工厂进行h获取
                        _factory = self.singleton_factory.get(key)
                        # 工厂如果没实例化对这个工厂进行实例化
                        if _factory is None:
                            _factory = self._create_object(key.object_to_assemble)
                            factory = cast(InterfaceFactory, _factory)
                            self.factory_object_cache[class_object] = factory
                            self.singleton_factory[key] = factory
                        break
        # 解析函数
        params = {}
        try:
            signature = inspect.signature(class_object.__init__)
        except ValueError as exc:
            self._logger.info("Module %s get initialize signature error", class_object.__name__)
            raise exc
        for name, parameter in signature.parameters.items():
            if name in ("self", "args", "kwargs"):
                continue
            if parameter.default != inspect.Parameter.empty:
                params[name] = parameter.default
            else:
                params[name] = None
        # 构建构造器注入所需要的参数
        for name, parameter in signature.parameters.items():
            if name in ("self", "args", "kwargs"):
                continue
            annotation = parameter.annotation
            instantiate = self.singleton_objects.get(annotation)
            if instantiate is None:
                instantiate = self.resolvable_objects.get(annotation)
            if instantiate is None:
                object_definition = self.object_definition_map.get(annotation)
                # 如果依赖未初始化 则创建依赖项
                if object_definition is not None:
                    instantiate = self._create_object(object_definition.class_object)
                    self.singleton_objects[object_definition.class_object] = instantiate
            if instantiate is None:
                # 怎么样检查参数不存在 该抛出异常
                raise NoSuchParameterException(
                    f"Cannot find the {name} parameter of type {annotation.__name__} required "
                    f"by the {class_object.__name__} component"
                )
            params[name] = instantiate
        # 将依赖项通过构造器注入到使用它的类中
        instantiation = class_object(**params)
        # 判断这个类是否归工厂管理 如果归则调用 get_object
        if factory is not None:
            _instantiation = factory.get_object(instantiation)
            if _instantiation is not None:
                self.singleton_objects[class_object] = instantiation
                return _instantiation
        self.singleton_objects[class_object] = instantiation
        return instantiation
