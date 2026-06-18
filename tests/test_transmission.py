"""
Unit tests for the transmission mechanics helpers in simulation/transmission.py.

All functions under test are pure (no side effects, no randomness) so every
test is completely deterministic.  The caller-supplied rng_sample pattern means
no mocking is required — we simply pass known float values.
"""

from __future__ import annotations

import pytest

from simulation.transmission import (
    LOCATION_MULTIPLIERS,
    exposure_occurred,
    infection_probability,
)

_BETA = 0.04


# ── LOCATION_MULTIPLIERS table ────────────────────────────────────────────────

def test_all_expected_locations_are_defined():
    expected = {"gq", "home", "school", "work", "community"}
    assert set(LOCATION_MULTIPLIERS.keys()) == expected


def test_location_multiplier_ordering():
    """Higher-risk environments must have strictly larger multipliers."""
    assert LOCATION_MULTIPLIERS["gq"]        > LOCATION_MULTIPLIERS["home"]
    assert LOCATION_MULTIPLIERS["home"]      > LOCATION_MULTIPLIERS["school"]
    assert LOCATION_MULTIPLIERS["school"]    > LOCATION_MULTIPLIERS["work"]
    assert LOCATION_MULTIPLIERS["work"]      > LOCATION_MULTIPLIERS["community"]


# ── infection_probability ─────────────────────────────────────────────────────

@pytest.mark.parametrize("location,multiplier", list(LOCATION_MULTIPLIERS.items()))
def test_infection_probability_applies_correct_multiplier(location, multiplier):
    beta = 0.05
    result = infection_probability(beta, location)
    assert result == pytest.approx(beta * multiplier)


def test_infection_probability_household_uses_2_5_multiplier():
    """Explicit regression: household multiplier must be exactly 2.5."""
    beta   = _BETA
    result = infection_probability(beta, "home")
    assert result == pytest.approx(beta * 2.5)


def test_infection_probability_gq_uses_3_5_multiplier():
    beta   = _BETA
    result = infection_probability(beta, "gq")
    assert result == pytest.approx(beta * 3.5)


def test_infection_probability_school_uses_1_8_multiplier():
    beta   = _BETA
    result = infection_probability(beta, "school")
    assert result == pytest.approx(beta * 1.8)


def test_infection_probability_work_uses_1_0_multiplier():
    beta   = _BETA
    result = infection_probability(beta, "work")
    assert result == pytest.approx(beta * 1.0)


def test_infection_probability_community_uses_0_4_multiplier():
    beta   = _BETA
    result = infection_probability(beta, "community")
    assert result == pytest.approx(beta * 0.4)


def test_infection_probability_scales_linearly_with_beta():
    loc = "home"
    p1 = infection_probability(0.02, loc)
    p2 = infection_probability(0.04, loc)
    assert p2 == pytest.approx(2 * p1)


def test_infection_probability_raises_on_unknown_location():
    with pytest.raises(KeyError):
        infection_probability(_BETA, "moon_base")


# ── exposure_occurred ─────────────────────────────────────────────────────────

def test_exposure_occurs_when_sample_strictly_below_threshold():
    p = infection_probability(_BETA, "home")   # 0.04 * 2.5 = 0.10
    sample_below = p - 1e-9
    assert exposure_occurred(_BETA, "home", sample_below) is True


def test_exposure_does_not_occur_when_sample_equals_threshold():
    p = infection_probability(_BETA, "home")
    assert exposure_occurred(_BETA, "home", p) is False


def test_exposure_does_not_occur_when_sample_above_threshold():
    p = infection_probability(_BETA, "home")
    sample_above = p + 1e-9
    assert exposure_occurred(_BETA, "home", sample_above) is False


def test_exposure_always_occurs_when_sample_is_zero():
    """rng_sample == 0 must always result in exposure (any beta > 0)."""
    for loc in LOCATION_MULTIPLIERS:
        assert exposure_occurred(_BETA, loc, 0.0) is True


def test_exposure_never_occurs_when_sample_is_one():
    """rng_sample == 1.0 can never be < any probability in [0, 1)."""
    for loc in LOCATION_MULTIPLIERS:
        assert exposure_occurred(_BETA, loc, 1.0) is False


@pytest.mark.parametrize("location", list(LOCATION_MULTIPLIERS.keys()))
def test_exposure_boundary_is_strict_less_than(location):
    """P(inf) is a strict threshold: sample must be *strictly* less than P."""
    p = infection_probability(_BETA, location)
    assert exposure_occurred(_BETA, location, p - 1e-12) is True
    assert exposure_occurred(_BETA, location, p)          is False


def test_household_interaction_correctly_applies_2_5_multiplier():
    """Regression test explicitly verifying household transmission logic.

    With beta=0.04 and M_home=2.5, P=0.10.
    A sample of 0.09 must result in exposure; 0.11 must not.
    """
    assert exposure_occurred(0.04, "home", 0.09) is True
    assert exposure_occurred(0.04, "home", 0.11) is False
