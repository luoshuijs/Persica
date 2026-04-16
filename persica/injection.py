from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InjectionMarker:
    kind: str
    key_attr: str | None = None


def inject() -> InjectionMarker:
    return InjectionMarker(kind="single")


def inject_all() -> InjectionMarker:
    return InjectionMarker(kind="all")


def inject_map(key_attr: str) -> InjectionMarker:
    return InjectionMarker(kind="map", key_attr=key_attr)
