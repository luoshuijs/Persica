from typing import Optional, Type


class ObjectDefinition:
    class_object: Type[object]

    is_factory: Optional[bool] = None

    def __init__(self, class_object: Type[object], is_factory: Optional[bool] = None):
        self.class_object = class_object
        self.is_factory = is_factory
