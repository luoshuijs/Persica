from typing import Optional, Type


class ObjectDefinition:
    """
    定义对象的结构，包括对象的类和是否是工厂。
    """

    class_object: Type[object]

    is_factory: Optional[bool] = None

    def __init__(self, class_object: Type[object], is_factory: Optional[bool] = None):
        self.class_object = class_object
        self.is_factory = is_factory
