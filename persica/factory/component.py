from typing import ClassVar, TypeVar

T = TypeVar("T")


class BaseComponent:
    __is_component__: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs):
        cls.__is_component__ = kwargs.get("component", True)


class AsyncInitComponent(BaseComponent):
    async def initialize(self):
        pass

    async def shutdown(self):
        pass


def component(cls: T) -> T:
    cls.__is_component__ = True
    return cls
