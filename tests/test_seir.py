"""
Unit tests for the SEIR state machine in FluAgent.

All tests use a deterministic duration sampler injected via the
``duration_sampler`` argument, so no test depends on random state or the
real dataset.  A minimal single-agent model is built from an in-memory
DataFrame for each test.
"""

from __future__ import annotations

import pandas as pd
import pytest

from simulation.agents import (
    FluAgent,
    HealthState,
    _ASYMPTOMATIC_RATE,
    _ELDERLY_AGE_THRESHOLD,
    _ELDERLY_PENALTY,
    _INCUBATION_MEAN,
    _INFECTIOUS_MEAN,
    _clamp_positive,
)
from simulation.model import FluModel


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_population(
    age: int = 30,
    work_id: str | None = "w1",
    school_id: str | None = None,
) -> pd.DataFrame:
    """Single-agent population DataFrame for isolated unit tests."""
    return pd.DataFrame({
        "sp_id":     ["p1"],
        "age":       [age],
        "sex":       ["M"],
        "sp_hh_id":  ["hh1"],
        "school_id": [school_id],
        "work_id":   [work_id],
        "sp_gq_id":  [None],
    })


def _get_agent(model: FluModel) -> FluAgent:
    return list(model.agents)[0]


def _fixed_sampler(value: float):
    """Return a duration sampler that always produces *value*."""
    return lambda mu, sigma: value


# ── clamp helper ──────────────────────────────────────────────────────────────

def test_clamp_positive_rounds_and_floors_at_one():
    assert _clamp_positive(0.0)   == 1
    assert _clamp_positive(-10.0) == 1
    assert _clamp_positive(2.4)   == 2
    assert _clamp_positive(2.6)   == 3


# ── Initial state ─────────────────────────────────────────────────────────────

def test_agent_starts_susceptible():
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)
    assert agent.health_state is HealthState.SUSCEPTIBLE


def test_susceptible_agent_does_not_advance_on_step():
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)
    agent.step()
    assert agent.health_state is HealthState.SUSCEPTIBLE
    assert agent._ticks_in_state == 0


# ── expose() ─────────────────────────────────────────────────────────────────

def test_expose_transitions_susceptible_to_exposed():
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)
    agent.expose()
    assert agent.health_state is HealthState.EXPOSED


def test_expose_sets_positive_state_duration():
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)
    agent._sampler = _fixed_sampler(_INCUBATION_MEAN)
    agent.expose()
    assert agent._state_duration == _clamp_positive(_INCUBATION_MEAN)


def test_expose_resets_tick_counter():
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)
    agent.expose()
    assert agent._ticks_in_state == 0


def test_expose_is_idempotent_when_already_exposed():
    """Calling expose() a second time must not reset the duration counter."""
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)
    agent._sampler = _fixed_sampler(10.0)
    agent.expose()
    original_duration = agent._state_duration

    # Simulate one tick so the counter advances
    agent.step()
    agent.expose()  # should be a no-op

    assert agent.health_state is HealthState.EXPOSED
    assert agent._state_duration == original_duration
    assert agent._ticks_in_state == 1  # counter was NOT reset


def test_expose_is_no_op_for_non_susceptible_states():
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)

    # Manually push to Recovered
    agent.health_state = HealthState.RECOVERED
    agent.expose()
    assert agent.health_state is HealthState.RECOVERED


# ── E → I transition ─────────────────────────────────────────────────────────

def test_exposed_transitions_to_infectious_after_exactly_d_e_ticks():
    """Agent must transition E → I after exactly _state_duration ticks."""
    duration = 5
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)
    agent._sampler = _fixed_sampler(float(duration))
    agent.expose()

    assert agent._state_duration == duration

    for tick in range(duration - 1):
        agent.step()
        assert agent.health_state is HealthState.EXPOSED, (
            f"Should still be EXPOSED after {tick + 1} ticks (duration={duration})"
        )

    agent.step()  # tick == duration → transition
    assert agent.health_state is HealthState.INFECTIOUS


def test_transition_to_infectious_resets_tick_counter():
    duration = 3
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)
    agent._sampler = _fixed_sampler(float(duration))
    agent.expose()

    for _ in range(duration):
        agent.step()

    assert agent._ticks_in_state == 0


# ── I → R transition ─────────────────────────────────────────────────────────

def test_infectious_transitions_to_recovered_after_exactly_d_i_ticks():
    """Agent must transition I → R after exactly the infectious duration."""
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)

    exp_dur = 2
    inf_dur = 4
    agent._sampler = _fixed_sampler(float(exp_dur))
    agent.expose()

    # Advance through incubation
    for _ in range(exp_dur):
        agent.step()
    assert agent.health_state is HealthState.INFECTIOUS

    # Now override sampler for infectious duration
    agent._sampler = _fixed_sampler(float(inf_dur))
    agent._state_duration = inf_dur
    agent._ticks_in_state = 0

    for tick in range(inf_dur - 1):
        agent.step()
        assert agent.health_state is HealthState.INFECTIOUS, (
            f"Should still be INFECTIOUS after {tick + 1} ticks (duration={inf_dur})"
        )

    agent.step()
    assert agent.health_state is HealthState.RECOVERED


def test_recovered_agent_stays_recovered():
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)
    agent.health_state = HealthState.RECOVERED
    agent.step()
    assert agent.health_state is HealthState.RECOVERED
    assert agent._ticks_in_state == 0


# ── Elderly penalty ───────────────────────────────────────────────────────────

def test_elderly_penalty_increases_infectious_duration():
    """Age > 65 must apply a 20 % duration penalty to D_I."""
    young_model = FluModel(
        population=_make_population(age=30), seed=0, initial_infected=0
    )
    young_agent = _get_agent(young_model)
    young_agent._sampler = _fixed_sampler(_INFECTIOUS_MEAN)

    elderly_model = FluModel(
        population=_make_population(age=_ELDERLY_AGE_THRESHOLD + 1),
        seed=0,
        initial_infected=0,
    )
    elderly_agent = _get_agent(elderly_model)
    elderly_agent._sampler = _fixed_sampler(_INFECTIOUS_MEAN)

    # Push both directly to Infectious so _transition_to_infectious() runs
    young_agent.health_state   = HealthState.EXPOSED
    elderly_agent.health_state = HealthState.EXPOSED
    young_agent._transition_to_infectious()
    elderly_agent._transition_to_infectious()

    expected_young   = _clamp_positive(_INFECTIOUS_MEAN)
    expected_elderly = _clamp_positive(_INFECTIOUS_MEAN * (1.0 + _ELDERLY_PENALTY))
    assert elderly_agent._state_duration == expected_elderly
    assert young_agent._state_duration   == expected_young
    assert elderly_agent._state_duration > young_agent._state_duration


def test_elderly_threshold_is_exclusive():
    """An agent aged exactly 65 does NOT receive the penalty (age > 65)."""
    model = FluModel(
        population=_make_population(age=_ELDERLY_AGE_THRESHOLD),
        seed=0,
        initial_infected=0,
    )
    agent = _get_agent(model)
    agent._sampler = _fixed_sampler(_INFECTIOUS_MEAN)
    agent.health_state = HealthState.EXPOSED
    agent._transition_to_infectious()
    assert agent._state_duration == _clamp_positive(_INFECTIOUS_MEAN)


# ── Asymptomatic flag ─────────────────────────────────────────────────────────

def test_asymptomatic_flag_is_set_on_infectious_transition():
    """is_asymptomatic must be assigned (True or False) when entering Infectious."""
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)
    assert agent.is_asymptomatic is False  # default before transition

    agent._sampler = _fixed_sampler(2.0)
    agent.expose()
    for _ in range(2):
        agent.step()

    assert agent.health_state is HealthState.INFECTIOUS
    assert isinstance(agent.is_asymptomatic, bool)


def test_asymptomatic_rate_converges_to_expected_proportion():
    """Over many agents, roughly 35 % should be flagged asymptomatic."""
    import random as rlib

    n = 500
    pop = pd.DataFrame({
        "sp_id":     [str(i) for i in range(n)],
        "age":       [30] * n,
        "sex":       ["M"] * n,
        "sp_hh_id":  [f"hh{i}" for i in range(n)],
        "school_id": [None] * n,
        "work_id":   [f"w{i}" for i in range(n)],
        "sp_gq_id":  [None] * n,
    })
    model = FluModel(population=pop, seed=42, initial_infected=0)
    agents = list(model.agents)

    # Force all to Infectious with a known sampler
    for agent in agents:
        agent._sampler = _fixed_sampler(1.0)
        agent.health_state = HealthState.EXPOSED
        agent._transition_to_infectious()

    asymptomatic_count = sum(1 for a in agents if a.is_asymptomatic)
    rate = asymptomatic_count / n
    # Allow ±10 % tolerance around 35 %
    assert abs(rate - _ASYMPTOMATIC_RATE) < 0.10, (
        f"Asymptomatic rate {rate:.2f} too far from expected {_ASYMPTOMATIC_RATE}"
    )


# ── Quarantine reset on recovery ──────────────────────────────────────────────

def test_quarantine_flag_cleared_on_recovery():
    model = FluModel(population=_make_population(), seed=0, initial_infected=0)
    agent = _get_agent(model)

    # Force agent into Infectious with quarantine flag set
    agent.health_state   = HealthState.INFECTIOUS
    agent.is_quarantined = True
    agent._state_duration = 1
    agent._ticks_in_state = 0

    agent.step()

    assert agent.health_state    is HealthState.RECOVERED
    assert agent.is_quarantined  is False
