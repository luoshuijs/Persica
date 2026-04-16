from persica.phase import Phase

DEFAULT_ORDER: int = 0


class BaseComponent:
    __order__: int = DEFAULT_ORDER
    __phase__: Phase | None = None

    def __init_subclass__(cls, **kwargs):
        order = kwargs.pop("order", None)
        phase = kwargs.pop("phase", None)
        super().__init_subclass__(**kwargs)

        if phase is not None and order is not None:
            raise TypeError("BaseComponent subclasses cannot define both phase and order")

        if phase is not None and not isinstance(phase, Phase):
            raise TypeError("BaseComponent phase must be a Phase enum value")

        if order is not None:
            cls.__order__ = order
            cls.__phase__ = None
        elif phase is not None:
            cls.__order__ = int(phase)
            cls.__phase__ = phase


class AsyncInitializingComponent(BaseComponent):
    async def initialize(self):
        pass

    async def shutdown(self):
        pass
