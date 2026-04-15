DEFAULT_ORDER: int = 0


class BaseComponent:
    __order__: int = DEFAULT_ORDER

    def __init_subclass__(cls, **kwargs):
        order = kwargs.pop("order", None)
        super().__init_subclass__(**kwargs)
        if order is not None:
            cls.__order__ = order


class AsyncInitializingComponent(BaseComponent):
    async def initialize(self):
        pass

    async def shutdown(self):
        pass
