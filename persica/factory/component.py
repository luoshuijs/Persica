DEFAULT_ORDER: int = 0


class BaseComponent:
    __order__: int = DEFAULT_ORDER

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        order = kwargs.get("order")
        if order is not None:
            cls.__order__ = order


class AsyncInitializingComponent(BaseComponent):

    async def initialize(self):
        pass

    async def shutdown(self):
        pass
