import inspect
import re
import sys
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, cast, get_args, get_origin

from persica.error import (
    AmbiguousDependencyException,
    InvalidInjectionConfigurationError,
    NoSuchParameterException,
)
from persica.factory.definition import ObjectDefinition
from persica.factory.interface import InterfaceFactory
from persica.injection import InjectionMarker
from persica.utils.logging import get_logger

if TYPE_CHECKING:
    from logging import Logger

_LOGGER = get_logger(__name__, "AbstractAutowireCapableFactory")
MAP_INJECTION_ARGUMENT_COUNT = 2


class AbstractAutowireCapableFactory:
    _logger: "Logger" = _LOGGER
    # 存储对象定义对应的加载顺序的映射表，key 为顺序，value 为 ObjectDefinition
    order_definitions: dict[int, list[ObjectDefinition]]
    # 存储对象定义的映射表，key 为对象的类，value 为 ObjectDefinition
    object_definitions: dict[type[object], ObjectDefinition]
    # 工厂缓存，缓存已经创建的工厂对象，key 为对象的类，value 为工厂实例
    factory_cache: dict[type[object], InterfaceFactory]
    # 存储已经实例化的单例对象，key 为对象的类，value 为对象实例
    singleton_objects: dict[type[object], object]
    # 存储已经实例化的工厂对象，key 为工厂类，value 为工厂实例
    singleton_factories: dict[type[InterfaceFactory], InterfaceFactory]
    # 存储外部可注入的对象，key 为对象的类，value 为对象实例
    external_objects: dict[type[object], object]
    # 存储运行时发布的可注入对象，key 为对象的类，value 为对象实例
    published_objects: dict[type[object], list[object]]
    # 按实际发布时间顺序存储运行时发布的可注入对象
    published_object_sequence: list[object]
    # 存储当前正在创建的对象类型，避免按需发布时递归回到自身
    creating_classes: set[type[object]]

    def __init__(self, external_objects: Iterable[object] | None = None):
        """
        初始化工厂，允许外部传入可解析的对象，并将它们存入 external_objects。
        """
        self.order_definitions = {}
        self.object_definitions = {}
        self.factory_cache = {}
        self.singleton_objects = {}
        self.singleton_factories = {}
        self.external_objects = {}
        self.published_objects = {}
        self.published_object_sequence = []
        self.creating_classes = set()

        if external_objects is not None:
            for obj in external_objects:
                original_class = obj.__class__
                self.external_objects.setdefault(original_class, obj)

    def add_external_object(self, external_objects: object):
        original_class = external_objects.__class__
        self.external_objects.setdefault(original_class, external_objects)

    def instantiate_all_objects(self):
        """
        实例化 object_definitions 中所有的对象。
        """
        self._logger.info("Instantiating all objects")
        ordered_classes: set[type[object]] = set()
        sorted_definition = sorted(self.order_definitions.items())
        for _, definitions in sorted_definition:
            for definition in definitions:
                ordered_classes.add(definition.class_object)
                self.get_object(definition.class_object)
        for definition in self.object_definitions.values():
            if definition.class_object in ordered_classes:
                continue
            self.get_object(definition.class_object)

    def get_object(self, cls: type[object]):
        """
        根据类获取对象实例，如果未创建则调用 create_object 方法创建。
        """
        definition = self.object_definitions.get(cls)
        if definition is None:
            self._logger.warning("No definition found for class %s", cls.__name__)
            return None

        if definition.is_factory:
            # 如果对象定义是工厂，则获取或创建工厂对象
            cls = cast("type[InterfaceFactory]", cls)
            obj = self.singleton_factories.get(cls)
            if obj is None:
                return self.create_object(cls)
        else:
            # 如果对象定义不是工厂，则获取或创建单例对象
            obj = self.singleton_objects.get(cls)
            if obj is None:
                return self.create_object(cls)
        return obj

    def create_object(self, cls: type[object]) -> object:
        """
        创建一个对象实例，支持依赖注入和工厂管理。
        """
        self._logger.info("Creating object %s", cls.__name__)
        definition = self.object_definitions.get(cls)
        self.creating_classes.add(cls)
        try:
            # 查找是否有该类的工厂
            factory = self._find_factory_for_class(cls)
            # 构建构造函数参数
            params = self._build_constructor_params(cls)
            # 创建对象
            obj = cls(**params)
            instance = obj
            # 如果该类有工厂管理，则通过工厂获取实例
            if factory is not None:
                factory_instance = factory.get_object(obj)
                if factory_instance is not None:
                    instance = factory_instance
            self._finalize_created_object(obj)
            # 如果没有工厂管理，直接返回对象
            if definition is not None and definition.is_factory:
                self.singleton_factories[cast("type[InterfaceFactory]", cls)] = cast("InterfaceFactory", instance)
                return instance
            self.singleton_objects[cls] = instance
            return instance
        finally:
            self.creating_classes.discard(cls)

    def _finalize_created_object(self, obj: object):
        self._inject_marked_properties(obj)
        published_objects = self._publish_objects(obj)
        try:
            after_inject = getattr(obj, "after_inject", None)
            if callable(after_inject):
                after_inject()
        except Exception:
            self._rollback_published_objects(published_objects)
            raise

    def _inject_marked_properties(self, obj: object):
        for name, annotation, marker in self._iter_injection_markers(obj.__class__):
            dependency = self._resolve_marked_property(obj.__class__, name, annotation, marker)
            setattr(obj, name, dependency)

    def _resolve_marked_property(
        self,
        cls: type[object],
        name: str,
        annotation: Any,
        marker: InjectionMarker,
    ) -> object:
        if marker.kind == "single":
            if not isinstance(annotation, type):
                raise InvalidInjectionConfigurationError(
                    f"Injected property {cls.__name__}.{name} must declare a concrete type annotation"
                )
            dependency = self._resolve_dependency(annotation, name)
            if dependency is None:
                raise NoSuchParameterException(
                    f"Cannot find the {name} property of type {annotation.__name__} required "
                    f"by the {cls.__name__} component"
                )
            return dependency

        if marker.kind == "all":
            dependency_type = self._extract_collection_injection_type(cls, name, annotation)
            return self._collect_compatible_objects(dependency_type)

        if marker.kind == "map":
            key_type, dependency_type = self._extract_map_injection_types(cls, name, annotation)
            dependencies_by_key: dict[object, object] = {}
            for dependency in self._collect_compatible_objects(dependency_type):
                if marker.key_attr is None or not hasattr(dependency, marker.key_attr):
                    raise InvalidInjectionConfigurationError(
                        f"Injected property {cls.__name__}.{name} requires key attribute {marker.key_attr!r} "
                        f"on {dependency.__class__.__name__}"
                    )
                key = getattr(dependency, marker.key_attr)
                if key is None:
                    raise InvalidInjectionConfigurationError(
                        f"Injected property {cls.__name__}.{name} resolved a None key from attribute "
                        f"{marker.key_attr!r} on {dependency.__class__.__name__}"
                    )
                if not isinstance(key, key_type):
                    raise InvalidInjectionConfigurationError(
                        f"Injected property {cls.__name__}.{name} resolved key {key!r} of type "
                        f"{key.__class__.__name__}, expected {key_type.__name__}"
                    )
                if key in dependencies_by_key:
                    raise InvalidInjectionConfigurationError(
                        f"Injected property {cls.__name__}.{name} resolved duplicate key {key!r} from "
                        f"attribute {marker.key_attr!r}"
                    )
                dependencies_by_key[key] = dependency
            return dependencies_by_key

        raise InvalidInjectionConfigurationError(f"Unsupported injection kind {marker.kind!r} on {cls.__name__}.{name}")

    def _iter_injection_markers(self, cls: type[object]) -> Iterable[tuple[str, Any, InjectionMarker]]:
        markers: list[tuple[str, Any, InjectionMarker]] = []
        seen_names: set[str] = set()
        for current_cls in cls.__mro__:
            for name, value in list(vars(current_cls).items()):
                if name in seen_names:
                    continue
                seen_names.add(name)
                if not isinstance(value, InjectionMarker):
                    continue
                annotation = self._resolve_effective_injected_annotation(cls, current_cls, name)
                markers.append((name, annotation, value))
        yield from reversed(markers)

    def _resolve_effective_injected_annotation(
        self, target_cls: type[object], marker_owner_cls: type[object], name: str
    ) -> Any:
        for current_cls in target_cls.__mro__:
            if name in getattr(current_cls, "__annotations__", {}):
                return self._resolve_class_annotation(current_cls, name)
            if current_cls is marker_owner_cls:
                break
        return self._resolve_class_annotation(marker_owner_cls, name)

    def _extract_collection_injection_type(self, cls: type[object], name: str, annotation: Any) -> type[object]:
        origin = get_origin(annotation)
        arguments = get_args(annotation)
        if origin is not list or len(arguments) != 1 or not isinstance(arguments[0], type):
            raise InvalidInjectionConfigurationError(
                f"Injected property {cls.__name__}.{name} using inject_all() must declare a list[T] annotation"
            )
        return cast("type[object]", arguments[0])

    def _extract_map_injection_types(
        self, cls: type[object], name: str, annotation: Any
    ) -> tuple[type[object], type[object]]:
        origin = get_origin(annotation)
        arguments = get_args(annotation)
        if (
            origin is not dict
            or len(arguments) != MAP_INJECTION_ARGUMENT_COUNT
            or not isinstance(arguments[0], type)
            or not isinstance(arguments[1], type)
        ):
            raise InvalidInjectionConfigurationError(
                f"Injected property {cls.__name__}.{name} using inject_map() must declare a dict[K, V] annotation"
            )
        return cast("type[object]", arguments[0]), cast("type[object]", arguments[1])

    def _collect_compatible_objects(self, annotation: type[object]) -> list[object]:
        candidate_publishers = self._find_candidate_publishers(
            annotation,
            exact_match=False,
            allow_declared_supertypes=False,
        )
        for publisher_cls in candidate_publishers:
            self.get_object(publisher_cls)

        collected: list[object] = []
        seen_ids: set[int] = set()

        def add_candidate(candidate: object):
            candidate_id = id(candidate)
            if candidate_id in seen_ids:
                return
            seen_ids.add(candidate_id)
            collected.append(candidate)

        for instance in self.singleton_objects.values():
            if isinstance(instance, annotation):
                add_candidate(instance)

        for instance in self.external_objects.values():
            if isinstance(instance, annotation):
                add_candidate(instance)

        for instance in self.published_object_sequence:
            if isinstance(instance, annotation):
                add_candidate(instance)

        for definition in self._iter_ordered_definitions():
            candidate_cls = definition.class_object
            if definition.is_factory or candidate_cls in self.creating_classes:
                continue
            if issubclass(candidate_cls, annotation):
                instance = self.get_object(definition.class_object)
                if isinstance(instance, annotation):
                    add_candidate(instance)

        return collected

    def _resolve_class_annotation(self, cls: type[object], name: str) -> Any:
        annotations = getattr(cls, "__annotations__", {})
        annotation = annotations.get(name)
        return self._resolve_annotation(
            annotation,
            globals_namespace=vars(sys.modules[cls.__module__]),
            locals_namespace=dict(vars(cls)),
            error_context=f"Injected property {cls.__name__}.{name}",
        )

    def _resolve_annotation(
        self,
        annotation: Any,
        *,
        globals_namespace: dict[str, Any],
        locals_namespace: dict[str, Any],
        error_context: str,
        suppress_resolution_errors: bool = False,
    ) -> Any:
        if not isinstance(annotation, str):
            return annotation

        try:
            return eval(annotation, globals_namespace, locals_namespace)  # noqa: S307
        except Exception as exc:
            if suppress_resolution_errors:
                return None
            raise InvalidInjectionConfigurationError(
                f"{error_context} has an unresolved annotation: {annotation}"
            ) from exc

    def _publish_objects(self, obj: object) -> list[object]:
        provide_objects = getattr(obj, "provide_objects", None)
        if not callable(provide_objects):
            return []
        published = provide_objects()
        if published is None:
            return []
        if not isinstance(published, list):
            raise InvalidInjectionConfigurationError(
                f"{obj.__class__.__name__}.provide_objects() must return a list of objects"
            )
        for published_object in published:
            self.published_objects.setdefault(published_object.__class__, []).append(published_object)
            self.published_object_sequence.append(published_object)
        return list(published)

    def _rollback_published_objects(self, published_objects: list[object]):
        for published_object in reversed(published_objects):
            published_instances = self.published_objects.get(published_object.__class__)
            if published_instances is not None:
                for index in range(len(published_instances) - 1, -1, -1):
                    if published_instances[index] is published_object:
                        del published_instances[index]
                        break
                if not published_instances:
                    del self.published_objects[published_object.__class__]
            for index in range(len(self.published_object_sequence) - 1, -1, -1):
                if self.published_object_sequence[index] is published_object:
                    del self.published_object_sequence[index]
                    break

    def _iter_ordered_definitions(self) -> Iterable[ObjectDefinition]:
        yielded_classes: set[type[object]] = set()
        for _, definitions in sorted(self.order_definitions.items()):
            for definition in definitions:
                yielded_classes.add(definition.class_object)
                yield definition
        for definition in self.object_definitions.values():
            if definition.class_object in yielded_classes:
                continue
            yield definition

    def _resolve_published_dependency(self, annotation: type[object], parameter_name: str) -> object | None:
        dependency = self._resolve_exact_published_object(annotation, parameter_name)
        if dependency is not None:
            return dependency

        candidate_publishers = self._find_candidate_publishers(
            annotation,
            exact_match=True,
            allow_declared_supertypes=False,
        )
        if not candidate_publishers:
            return None

        for publisher_cls in candidate_publishers:
            self.get_object(publisher_cls)
        return self._resolve_exact_published_object(annotation, parameter_name)

    def _resolve_exact_published_object(self, annotation: type[object], parameter_name: str) -> object | None:
        exact_published = self.published_objects.get(annotation)
        if exact_published is not None:
            if len(exact_published) > 1:
                raise AmbiguousDependencyException(
                    f"Multiple compatible dependencies found for parameter {parameter_name} of type "
                    f"{annotation.__name__}: {', '.join(obj.__class__.__name__ for obj in exact_published)}"
                )
            return exact_published[0]

        return None

    def _resolve_compatible_published_dependency(self, annotation: type[object], parameter_name: str) -> object | None:
        dependency = self._resolve_compatible_published_object(annotation, parameter_name)
        if dependency is not None:
            return dependency

        candidate_publishers = self._find_candidate_publishers(
            annotation,
            exact_match=False,
            allow_declared_supertypes=False,
        )
        if not candidate_publishers:
            return None

        for publisher_cls in candidate_publishers:
            self.get_object(publisher_cls)
        return self._resolve_compatible_published_object(annotation, parameter_name)

    def _resolve_compatible_published_object(self, annotation: type[object], parameter_name: str) -> object | None:
        compatible_published = {
            candidate_cls: instances
            for candidate_cls, instances in self.published_objects.items()
            if issubclass(candidate_cls, annotation)
        }
        compatible_count = sum(len(instances) for instances in compatible_published.values())
        if compatible_count > 1:
            raise AmbiguousDependencyException(
                f"Multiple compatible dependencies found for parameter {parameter_name} of type "
                f"{annotation.__name__}: {', '.join(candidate_cls.__name__ for candidate_cls, instances in compatible_published.items() for _ in instances)}"
            )
        if compatible_published:
            return next(iter(compatible_published.values()))[0]
        return None

    def _find_candidate_publishers(
        self,
        annotation: type[object],
        *,
        exact_match: bool,
        allow_declared_supertypes: bool = True,
    ) -> list[type[object]]:
        candidate_publishers: list[type[object]] = []
        for definition in self._iter_ordered_definitions():
            publisher_cls = definition.class_object
            if (
                definition.is_factory
                or publisher_cls in self.singleton_objects
                or publisher_cls in self.creating_classes
            ):
                continue
            published_types, unresolved_error, unresolved_annotation = self._get_published_types(publisher_cls)
            if unresolved_error is not None and self._is_relevant_unresolved_publisher_annotation(
                annotation,
                unresolved_annotation,
                exact_match=exact_match,
                allow_declared_supertypes=allow_declared_supertypes,
            ):
                raise unresolved_error
            if exact_match and any(published_type == annotation for published_type in published_types):
                candidate_publishers.append(publisher_cls)
                continue
            if not exact_match and any(
                issubclass(published_type, annotation)
                or (
                    allow_declared_supertypes
                    and published_type is not object
                    and issubclass(annotation, published_type)
                )
                for published_type in published_types
            ):
                candidate_publishers.append(publisher_cls)
        return candidate_publishers

    def _get_published_types(
        self, cls: type[object]
    ) -> tuple[tuple[type[object], ...], InvalidInjectionConfigurationError | None, str | None]:
        provide_objects = getattr(cls, "provide_objects", None)
        if not callable(provide_objects):
            return (), None, None

        try:
            signature = inspect.signature(provide_objects, eval_str=False)
        except ValueError:
            return (), None, None

        raw_return_annotation = signature.return_annotation

        resolved_return_annotation = self._resolve_annotation(
            raw_return_annotation,
            globals_namespace=provide_objects.__globals__,
            locals_namespace=dict(vars(cls)),
            error_context=f"{cls.__name__}.provide_objects() return annotation",
            suppress_resolution_errors=True,
        )
        if resolved_return_annotation is None and isinstance(raw_return_annotation, str):
            unresolved_error = InvalidInjectionConfigurationError(
                f"{cls.__name__}.provide_objects() return annotation has an unresolved annotation: {raw_return_annotation}"
            )
            return (), unresolved_error, raw_return_annotation

        return self._extract_published_types(resolved_return_annotation), None, None

    def _is_relevant_unresolved_publisher_annotation(
        self,
        annotation: type[object],
        unresolved_annotation: str | None,
        *,
        exact_match: bool,
        allow_declared_supertypes: bool,
    ) -> bool:
        if unresolved_annotation is None:
            return False
        candidate_types = {annotation}
        if not exact_match:
            candidate_types.update(self._iter_subclasses(annotation))
            candidate_types.update(
                candidate_cls
                for candidate_cls in self.object_definitions
                if candidate_cls is not annotation and issubclass(candidate_cls, annotation)
            )
            candidate_types.update(
                candidate_cls
                for candidate_cls in self.published_objects
                if candidate_cls is not annotation and issubclass(candidate_cls, annotation)
            )
        if allow_declared_supertypes:
            candidate_types.update(base for base in annotation.__mro__[1:] if base is not object)
            candidate_types.update(
                base
                for candidate_cls in self.object_definitions
                if candidate_cls is not annotation and issubclass(candidate_cls, annotation)
                for base in candidate_cls.__mro__[1:]
                if base is not object
            )
            candidate_types.update(
                base
                for candidate_cls in self.published_objects
                if candidate_cls is not annotation and issubclass(candidate_cls, annotation)
                for base in candidate_cls.__mro__[1:]
                if base is not object
            )

        unresolved_dotted_type_names = set(
            re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b", unresolved_annotation)
        )
        unresolved_simple_type_names = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", unresolved_annotation))

        known_types = set(candidate_types)
        known_types.update(self.object_definitions)
        known_types.update(self.published_objects)
        for candidate_type in candidate_types:
            known_types.update(self._iter_module_visible_types(candidate_type.__module__))

        simple_name_counts: dict[str, int] = {}
        for known_type in known_types:
            simple_name_counts[known_type.__name__] = simple_name_counts.get(known_type.__name__, 0) + 1

        precise_candidate_names = {
            name
            for candidate_type in candidate_types
            for name in (candidate_type.__qualname__, f"{candidate_type.__module__}.{candidate_type.__qualname__}")
        }
        if precise_candidate_names & unresolved_dotted_type_names:
            return True

        unique_simple_candidate_names = {
            candidate_type.__name__
            for candidate_type in candidate_types
            if simple_name_counts.get(candidate_type.__name__) == 1
        }
        return bool(unique_simple_candidate_names & unresolved_simple_type_names)

    def _iter_module_visible_types(self, module_name: str) -> set[type[object]]:
        module = sys.modules.get(module_name)
        if module is None:
            return set()

        discovered: set[type[object]] = set()
        for value in vars(module).values():
            if not isinstance(value, type):
                continue
            discovered.add(value)
            for nested_value in vars(value).values():
                if isinstance(nested_value, type):
                    discovered.add(nested_value)
        return discovered

    def _iter_subclasses(self, annotation: type[object]) -> set[type[object]]:
        discovered: set[type[object]] = set()
        pending = list(annotation.__subclasses__())
        while pending:
            subclass = pending.pop()
            if subclass in discovered:
                continue
            discovered.add(subclass)
            pending.extend(subclass.__subclasses__())
        return discovered

    def _extract_published_types(self, annotation: Any) -> tuple[type[object], ...]:
        if annotation in (inspect.Signature.empty, None):
            return ()
        if isinstance(annotation, type):
            return (annotation,)

        origin = get_origin(annotation)
        if origin is None:
            return ()

        extracted: list[type[object]] = []
        for argument in get_args(annotation):
            if argument is Ellipsis:
                continue
            extracted.extend(self._extract_published_types(argument))
        return tuple(extracted)

    def _find_factory_for_class(self, cls: type[object]) -> InterfaceFactory | None:
        """
        查找与给定类对应的工厂，如果没有找到则返回 None。
        """
        factory = self.factory_cache.get(cls)
        if factory is not None:
            return factory

        exact_matches: list[type[InterfaceFactory]] = []
        compatible_matches: list[type[InterfaceFactory]] = []
        for key, definition in self.object_definitions.items():
            if not definition.is_factory:
                continue
            factory_cls = cast("type[InterfaceFactory]", key)
            target_class = factory_cls.get_class()
            if target_class == cls:
                exact_matches.append(factory_cls)
                continue
            if issubclass(cls, target_class):
                compatible_matches.append(factory_cls)

        selected_factory_cls: type[InterfaceFactory] | None = None
        if len(exact_matches) == 1:
            selected_factory_cls = exact_matches[0]
        elif len(exact_matches) > 1:
            raise AmbiguousDependencyException(f"Multiple factories exactly match the {cls.__name__} product")
        elif len(compatible_matches) == 1:
            selected_factory_cls = compatible_matches[0]
        elif len(compatible_matches) > 1:
            raise AmbiguousDependencyException(f"Multiple compatible factories found for the {cls.__name__} product")

        if selected_factory_cls is None:
            return None

        factory_instance = self.singleton_factories.get(selected_factory_cls)
        if factory_instance is None:
            factory_instance = cast("InterfaceFactory", self.create_object(selected_factory_cls))

        self.factory_cache[cls] = factory_instance
        self.singleton_factories[selected_factory_cls] = factory_instance
        return factory_instance

    def _build_constructor_params(self, cls: type[object]) -> dict[str, Any]:
        """
        构建构造函数参数，支持依赖注入和默认值处理。
        """
        try:
            # 获取构造函数签名，并设置 eval_str=True 以支持 Python 3.10+ 的字符串注解
            signature = inspect.signature(cls.__init__, eval_str=True)
        except ValueError as exc:
            self._logger.exception("Failed to retrieve __init__ signature for %s: %s", cls.__name__, exc_info=exc)
            raise

        params: dict[str, Any] = {}
        for name, parameter in signature.parameters.items():
            if name in ("self", "args", "kwargs"):
                continue
            annotation = parameter.annotation
            instance = self._resolve_dependency(annotation, name)
            if instance is None:
                if parameter.default != inspect.Parameter.empty:
                    instance = parameter.default
                else:
                    raise NoSuchParameterException(
                        f"Cannot find the {name} parameter of type {annotation.__name__} required "
                        f"by the {cls.__name__} component"
                    )
            params[name] = instance
        return params

    def _resolve_dependency(self, annotation: Any, parameter_name: str) -> object | None:  # noqa: PLR0911, PLR0912
        if not isinstance(annotation, type):
            return None

        exact_singleton = self.singleton_objects.get(annotation)
        if exact_singleton is not None:
            return exact_singleton

        exact_external = self.external_objects.get(annotation)
        if exact_external is not None:
            return exact_external

        exact_definition = self.object_definitions.get(annotation)
        if exact_definition is not None:
            return self.get_object(exact_definition.class_object)

        published_dependency = self._resolve_published_dependency(annotation, parameter_name)
        if published_dependency is not None:
            return published_dependency

        compatible_candidates: dict[type[object], tuple[str, object | ObjectDefinition]] = {}
        for candidate_cls, instance in self.singleton_objects.items():
            if issubclass(candidate_cls, annotation):
                compatible_candidates[candidate_cls] = ("singleton", instance)
        for candidate_cls, instance in self.external_objects.items():
            if issubclass(candidate_cls, annotation) and candidate_cls not in compatible_candidates:
                compatible_candidates[candidate_cls] = ("external", instance)
        for candidate_cls, definition in self.object_definitions.items():
            if issubclass(candidate_cls, annotation) and candidate_cls not in compatible_candidates:
                compatible_candidates[candidate_cls] = ("definition", definition)

        if len(compatible_candidates) > 1:
            raise AmbiguousDependencyException(
                f"Multiple compatible dependencies found for parameter {parameter_name} of type "
                f"{annotation.__name__}: {', '.join(candidate_cls.__name__ for candidate_cls in compatible_candidates)}"
            )
        if not compatible_candidates:
            return self._resolve_compatible_published_dependency(annotation, parameter_name)

        _, (source, value) = next(iter(compatible_candidates.items()))
        if source == "definition":
            definition = cast("ObjectDefinition", value)
            return self.get_object(definition.class_object)
        return cast("object", value)
