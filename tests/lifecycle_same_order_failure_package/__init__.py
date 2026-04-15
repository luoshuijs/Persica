import asyncio

events: list[str] = []
_state: dict[str, asyncio.Event | None] = {"initialize_gate": None}


def reset_events() -> None:
    events.clear()
    _state["initialize_gate"] = asyncio.Event()


def get_initialize_gate() -> asyncio.Event:
    gate = _state["initialize_gate"]
    if gate is None:
        gate = asyncio.Event()
        _state["initialize_gate"] = gate
    return gate
