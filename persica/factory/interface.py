from typing import Generic, TypeVar, Type, Optional

T = TypeVar("T", bound=object)


class InterfaceFactory(Generic[T]):
    object_to_assemble: Type[T]

    def get_object(self, object_to_assemble: Optional[Type[T]]) -> T:
        pass
