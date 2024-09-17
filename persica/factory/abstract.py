import inspect
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, Type, Union, cast

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
    resolvable_objects: Dict[Type[object], object] = {}

    def __init__(self, resolvable_objects: Optional[Iterable[object]] = None):
        if resolvable_objects is not None:
            for k in resolvable_objects:
                original_class: "Type[object]" = k.__class__
                self.resolvable_objects.setdefault(original_class, k)

    def instantiate_object(self):
        self._logger.info("Instantiate Object")

        for _, value in self.object_definition_map.items():
            self._get_object(value)

    def _get_object(self, definition: ObjectDefinition):
        __cls = definition.class_object

        if definition.is_factory:
            __cls = cast(Type[InterfaceFactory], __cls)
            __obj = self.singleton_factory.get(__cls)
            if __obj is None:
                return self._create_object(__cls)
        else:
            __obj = self.singleton_objects.get(__cls)
            if __obj is None:
                return self._create_object(__cls)

    def _create_object(self, _cls: Type[object]) -> object:
        self._logger.info("create object %s", _cls.__name__)
        # 检查这个 class_object 是否需要指定工厂管理
        factory_object = self.factory_object_cache.get(_cls)
        if factory_object is None:
            # 遍历 object_definition_nmap 查找是否有对应的工厂
            for key, _object_definition in self.object_definition_map.items():
                # 判断是否为工厂
                if _object_definition.is_factory:
                    _factory_cls = cast(Type[InterfaceFactory], key)
                    # 判断这个工厂是否为 _cls 的工厂 或者是 包括 _cls 的子类
                    if issubclass(_cls, _factory_cls.object_to_assemble):
                        # 如果存在对工厂进行获取
                        _factory = self.singleton_factory.get(_factory_cls)
                        # 工厂如果没实例化对这个工厂进行实例化
                        if _factory is None:
                            _factory_obj = self._create_object(_factory_cls)
                            factory_object = cast(InterfaceFactory, _factory_obj)
                            self.factory_object_cache[_cls] = factory_object
                            self.singleton_factory[_factory_cls] = factory_object
                        break
        # 解析函数
        params: Dict[str, Any] = {}
        try:
            signature = inspect.signature(_cls.__init__)
        except ValueError as exc:
            self._logger.info("Module %s get initialize signature error", _cls.__name__)
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
                # 参数不存在 抛出异常
                raise NoSuchParameterException(
                    f"Cannot find the {name} parameter of type {annotation.__name__} required "
                    f"by the {_cls.__name__} component"
                )
            params[name] = instantiate
        # 将依赖项通过构造器注入到使用它的类中
        _obj = _cls(**params)
        # 判断这个类是否归工厂管理 如果归则调用 get_object
        if factory_object is not None:
            _instantiation = factory_object.get_object(_obj)
            if _instantiation is not None:
                self.singleton_objects[_cls] = _obj
                return _instantiation
        self.singleton_objects[_cls] = _obj
        return _obj
