import pytest

from persica import Phase, inject, inject_all, inject_map
from persica import Phase as PublicPhase
from persica import inject as public_inject
from persica import inject_all as public_inject_all
from persica import inject_map as public_inject_map
from persica.factory.component import BaseComponent

EXPECTED_PHASE_VALUES = {
    Phase.DEPENDENCY: 10,
    Phase.REPOSITORY: 20,
    Phase.SERVICE: 30,
    Phase.COMMAND: 40,
    Phase.JOB: 50,
}


def test_injection_helpers_return_distinct_marker_configurations():
    single = inject()
    all_values = inject_all()
    mapped = inject_map("name")

    assert single.kind == "single"
    assert single.key_attr is None
    assert all_values.kind == "all"
    assert all_values.key_attr is None
    assert mapped.kind == "map"
    assert mapped.key_attr == "name"


def test_public_api_exports_are_importable_from_persica():
    assert PublicPhase is Phase
    assert public_inject is inject
    assert public_inject_all is inject_all
    assert public_inject_map is inject_map


def test_phase_values_are_stable_and_ordered():
    for phase, expected_value in EXPECTED_PHASE_VALUES.items():
        assert phase == expected_value
    assert list(Phase) == [
        Phase.DEPENDENCY,
        Phase.REPOSITORY,
        Phase.SERVICE,
        Phase.COMMAND,
        Phase.JOB,
    ]


def test_component_phase_keyword_sets_order_attribute():
    class PhasedComponent(BaseComponent, phase=Phase.JOB):
        pass

    assert PhasedComponent.__order__ == Phase.JOB


def test_component_phase_and_order_keywords_conflict():
    with pytest.raises(TypeError, match="phase.*order"):

        class InvalidComponent(BaseComponent, phase=Phase.SERVICE, order=1):
            pass


def test_component_phase_keyword_requires_phase_enum_value():
    with pytest.raises(TypeError, match="Phase"):

        class InvalidPhaseComponent(BaseComponent, phase="service"):
            pass
