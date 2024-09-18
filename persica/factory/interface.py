from typing import Generic, Optional, Type, TypeVar, get_args

T = TypeVar("T", bound=object)


class _NotInterfaceFactory:
    pass


class InterfaceFactory(Generic[T]):
    object_to_assemble: Type[T]

    def get_objects(self, object_to_assemble: Optional[T]) -> T:
        pass

    @classmethod
    def get_object(cls) -> Type[T]:
        if hasattr(cls, "object_to_assemble"):
            return cls.object_to_assemble
        orig_bases = getattr(cls, "__orig_bases__", ())
        for base in orig_bases:
            if not hasattr(base, "get_objects"):
                continue
            if hasattr(base, "__origin__"):
                type_args = get_args(base)
                if type_args:
                    cls.object_to_assemble = type_args[0]
                    return cls.object_to_assemble
        raise NotImplementedError(
            f"{cls.__name__} must specify a generic type parameter or define 'object_to_assemble'"
        )
