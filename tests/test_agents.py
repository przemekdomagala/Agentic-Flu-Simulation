"""
Unit tests for FluAgent and FluModel.

Tests verify:
- FluModel spawns the exact number of agents matching the input DataFrame.
- Each agent carries the correct demographic attributes.
- All agents start in the Susceptible state.
- Sentinel / None values are handled correctly.
- FluModel works with an empty population without raising.
"""

import pandas as pd
import pytest

from simulation.agents import FluAgent, HealthState
from simulation.model import FluModel


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

def make_population(*rows: dict) -> pd.DataFrame:
    """Build a minimal population DataFrame for testing."""
    return pd.DataFrame(
        rows,
        columns=["sp_id", "age", "sex", "sp_hh_id", "school_id", "work_id", "sp_gq_id"],
    )


HOUSEHOLD_ROW = {
    "sp_id": "1001",
    "age": "35",
    "sex": "F",
    "sp_hh_id": "HH001",
    "school_id": None,
    "work_id": "WK999",
    "sp_gq_id": None,
}

GQ_ROW = {
    "sp_id": "2001",
    "age": "22",
    "sex": "M",
    "sp_hh_id": None,
    "school_id": None,
    "work_id": None,
    "sp_gq_id": "GQ042",
}

STUDENT_ROW = {
    "sp_id": "3001",
    "age": "12",
    "sex": "F",
    "sp_hh_id": "HH002",
    "school_id": "SCH007",
    "work_id": None,
    "sp_gq_id": None,
}


@pytest.fixture()
def small_model() -> FluModel:
    population = make_population(HOUSEHOLD_ROW, GQ_ROW, STUDENT_ROW)
    return FluModel(population=population, seed=0, initial_infected=0)


# ------------------------------------------------------------------
# Agent count
# ------------------------------------------------------------------

def test_model_spawns_correct_number_of_agents(small_model: FluModel) -> None:
    assert len(small_model.agents) == 3


def test_model_with_empty_population_has_no_agents() -> None:
    empty = make_population()
    model = FluModel(population=empty, seed=0)
    assert len(model.agents) == 0


def test_larger_population_spawns_all_agents() -> None:
    rows = [
        {"sp_id": str(i), "age": "30", "sex": "M",
         "sp_hh_id": f"HH{i}", "school_id": None, "work_id": None, "sp_gq_id": None}
        for i in range(100)
    ]
    population = pd.DataFrame(rows)
    model = FluModel(population=population, seed=0)
    assert len(model.agents) == 100


# ------------------------------------------------------------------
# Agent types
# ------------------------------------------------------------------

def test_all_agents_are_flu_agents(small_model: FluModel) -> None:
    for agent in small_model.agents:
        assert isinstance(agent, FluAgent)


# ------------------------------------------------------------------
# Attribute mapping
# ------------------------------------------------------------------

def _get_agent_by_sp_id(model: FluModel, sp_id: str) -> FluAgent:
    for agent in model.agents:
        if agent.sp_id == sp_id:
            return agent
    raise KeyError(f"No agent with sp_id={sp_id!r}")


def test_household_agent_attributes(small_model: FluModel) -> None:
    agent = _get_agent_by_sp_id(small_model, "1001")
    assert agent.age == 35
    assert agent.sex == "F"
    assert agent.sp_hh_id == "HH001"
    assert agent.work_id == "WK999"
    assert agent.school_id is None
    assert agent.sp_gq_id is None


def test_gq_agent_attributes(small_model: FluModel) -> None:
    agent = _get_agent_by_sp_id(small_model, "2001")
    assert agent.age == 22
    assert agent.sex == "M"
    assert agent.sp_hh_id is None
    assert agent.sp_gq_id == "GQ042"
    assert agent.work_id is None


def test_student_agent_attributes(small_model: FluModel) -> None:
    agent = _get_agent_by_sp_id(small_model, "3001")
    assert agent.school_id == "SCH007"
    assert agent.sp_hh_id == "HH002"
    assert agent.work_id is None


# ------------------------------------------------------------------
# Initial health state
# ------------------------------------------------------------------

def test_all_agents_start_susceptible(small_model: FluModel) -> None:
    for agent in small_model.agents:
        assert agent.health_state == HealthState.SUSCEPTIBLE


# ------------------------------------------------------------------
# Unique IDs
# ------------------------------------------------------------------

def test_all_agents_have_unique_mesa_ids(small_model: FluModel) -> None:
    ids = [agent.unique_id for agent in small_model.agents]
    assert len(ids) == len(set(ids)), "Duplicate Mesa unique_ids detected."


# ------------------------------------------------------------------
# Determinism
# ------------------------------------------------------------------

def test_same_seed_produces_same_agent_ids() -> None:
    population = make_population(HOUSEHOLD_ROW, GQ_ROW, STUDENT_ROW)
    model_a = FluModel(population=population, seed=7)
    model_b = FluModel(population=population, seed=7)
    ids_a = sorted(a.unique_id for a in model_a.agents)
    ids_b = sorted(a.unique_id for a in model_b.agents)
    assert ids_a == ids_b
