class ObjectDefinition:
    """
    定义对象的结构，包括对象的类和是否是工厂。
    """

    class_object: type[object]

    is_factory: bool | None = None

    def __init__(self, class_object: type[object], is_factory: bool | None = None):
        self.class_object = class_object
        self.is_factory = is_factory
