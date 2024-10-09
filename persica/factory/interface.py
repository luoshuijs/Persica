from typing import Generic, TypeVar, get_args

T = TypeVar("T", bound=object)


class InterfaceFactory(Generic[T]):
    # 表示该工厂所管理的目标类
    target_class: type[T]

    def get_object(self, obj: T | None) -> T:
        """
        返回与传入对象相关的对象实例。可根据具体实现决定返回相同或不同的实例。
        """
        raise NotImplementedError("Subclasses must implement this method")

    @classmethod
    def get_class(cls) -> type[T]:
        """
        获取该工厂管理的目标类。
        """
        if hasattr(cls, "target_class"):
            return cls.target_class
        # 检查泛型参数以获取目标类
        orig_bases = getattr(cls, "__orig_bases__", ())
        for base in orig_bases:
            if not hasattr(base, "get_object"):
                continue
            if hasattr(base, "__origin__"):
                type_args = get_args(base)
                if type_args:
                    cls.target_class = type_args[0]
                    return cls.target_class
        raise NotImplementedError(f"{cls.__name__} must specify a generic type parameter or define 'target_class'")
