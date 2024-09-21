from typing import ClassVar, Optional, TypeVar

T = TypeVar("T")
DEFAULT_ORDER: int = 0


class BaseComponent:
    __is_component__: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs):
        cls.__is_component__ = kwargs.get("component", True)


class AsyncInitializingComponent(BaseComponent):
    order: Optional[int] = DEFAULT_ORDER

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        order = kwargs.get("order")
        if order is not None:
            cls.order = order

    async def initialize(self):
        pass

    async def shutdown(self):
        pass


def component(cls: T) -> T:
    cls.__is_component__ = True
    return cls
