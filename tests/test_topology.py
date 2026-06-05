"""
Unit tests for TopologyBuilder (Task 3).

Tests verify graph integrity:
- Nodes in each sub-graph correspond to the correct agents.
- Edges only connect agents that share the same cluster attribute.
- No cross-group edges exist.
- Agents without a valid attribute have no edges in that sub-graph.
- Isolated (no-group) agents still appear as nodes.
"""

import pandas as pd
import pytest

from simulation.model import FluModel
from simulation.topology import TopologyBuilder


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_population(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["sp_id", "age", "sex", "sp_hh_id", "school_id", "work_id", "sp_gq_id"],
    )


def build_model_and_topology(rows: list[dict]) -> tuple[FluModel, TopologyBuilder]:
    population = make_population(*rows)
    model = FluModel(population=population, seed=0)
    return model, model.topology


def agent_by_sp_id(model: FluModel, sp_id: str):
    for agent in model.agents:
        if agent.sp_id == sp_id:
            return agent
    raise KeyError(sp_id)


# ------------------------------------------------------------------
# Shared population fixture used by most tests
# ------------------------------------------------------------------
#
# Two households: HH_A (agents 1, 2), HH_B (agents 3, 4, 5)
# Two schools:    SCH_1 (agents 1, 3), SCH_2 (agents 6)
# Two workplaces: WK_X (agents 2, 4), WK_Y (agents 5)
# One GQ:         GQ_Z (agents 7, 8)
# Agent 9: no household, no gq, no school, no work — fully isolated
#
ROWS = [
    {"sp_id": "1", "age": "12", "sex": "F", "sp_hh_id": "HH_A", "school_id": "SCH_1", "work_id": None,  "sp_gq_id": None},
    {"sp_id": "2", "age": "40", "sex": "M", "sp_hh_id": "HH_A", "school_id": None,    "work_id": "WK_X","sp_gq_id": None},
    {"sp_id": "3", "age": "10", "sex": "F", "sp_hh_id": "HH_B", "school_id": "SCH_1", "work_id": None,  "sp_gq_id": None},
    {"sp_id": "4", "age": "38", "sex": "M", "sp_hh_id": "HH_B", "school_id": None,    "work_id": "WK_X","sp_gq_id": None},
    {"sp_id": "5", "age": "35", "sex": "F", "sp_hh_id": "HH_B", "school_id": None,    "work_id": "WK_Y","sp_gq_id": None},
    {"sp_id": "6", "age": "15", "sex": "M", "sp_hh_id": None,   "school_id": "SCH_2", "work_id": None,  "sp_gq_id": None},
    {"sp_id": "7", "age": "20", "sex": "F", "sp_hh_id": None,   "school_id": None,    "work_id": None,  "sp_gq_id": "GQ_Z"},
    {"sp_id": "8", "age": "22", "sex": "M", "sp_hh_id": None,   "school_id": None,    "work_id": None,  "sp_gq_id": "GQ_Z"},
    {"sp_id": "9", "age": "50", "sex": "F", "sp_hh_id": None,   "school_id": None,    "work_id": None,  "sp_gq_id": None},
]


@pytest.fixture(scope="module")
def model_and_topology():
    return build_model_and_topology(ROWS)


# ------------------------------------------------------------------
# All agents appear as nodes in every graph
# ------------------------------------------------------------------

def test_all_agents_are_nodes_in_home_graph(model_and_topology):
    model, topology = model_and_topology
    expected_ids = {a.unique_id for a in model.agents}
    assert expected_ids == set(topology.G_home.nodes)


def test_all_agents_are_nodes_in_school_graph(model_and_topology):
    model, topology = model_and_topology
    expected_ids = {a.unique_id for a in model.agents}
    assert expected_ids == set(topology.G_school.nodes)


def test_all_agents_are_nodes_in_work_graph(model_and_topology):
    model, topology = model_and_topology
    expected_ids = {a.unique_id for a in model.agents}
    assert expected_ids == set(topology.G_work.nodes)


def test_all_agents_are_nodes_in_gq_graph(model_and_topology):
    model, topology = model_and_topology
    expected_ids = {a.unique_id for a in model.agents}
    assert expected_ids == set(topology.G_gq.nodes)


# ------------------------------------------------------------------
# G_home integrity
# ------------------------------------------------------------------

def test_home_graph_connects_household_members(model_and_topology):
    model, topology = model_and_topology
    a1 = agent_by_sp_id(model, "1")
    a2 = agent_by_sp_id(model, "2")
    assert topology.G_home.has_edge(a1.unique_id, a2.unique_id), (
        "Agents 1 and 2 share HH_A but are not connected in G_home."
    )


def test_home_graph_does_not_cross_households(model_and_topology):
    model, topology = model_and_topology
    a1 = agent_by_sp_id(model, "1")
    a3 = agent_by_sp_id(model, "3")
    assert not topology.G_home.has_edge(a1.unique_id, a3.unique_id), (
        "Agents 1 (HH_A) and 3 (HH_B) should not be connected in G_home."
    )


def test_home_graph_hh_b_is_fully_connected(model_and_topology):
    model, topology = model_and_topology
    a3 = agent_by_sp_id(model, "3")
    a4 = agent_by_sp_id(model, "4")
    a5 = agent_by_sp_id(model, "5")
    assert topology.G_home.has_edge(a3.unique_id, a4.unique_id)
    assert topology.G_home.has_edge(a3.unique_id, a5.unique_id)
    assert topology.G_home.has_edge(a4.unique_id, a5.unique_id)


def test_agent_without_household_has_no_home_edges(model_and_topology):
    model, topology = model_and_topology
    a9 = agent_by_sp_id(model, "9")
    assert topology.G_home.degree(a9.unique_id) == 0


# ------------------------------------------------------------------
# G_school integrity
# ------------------------------------------------------------------

def test_school_graph_connects_same_school(model_and_topology):
    model, topology = model_and_topology
    a1 = agent_by_sp_id(model, "1")
    a3 = agent_by_sp_id(model, "3")
    assert topology.G_school.has_edge(a1.unique_id, a3.unique_id), (
        "Agents 1 and 3 share SCH_1 but are not connected in G_school."
    )


def test_school_graph_does_not_cross_schools(model_and_topology):
    model, topology = model_and_topology
    a1 = agent_by_sp_id(model, "1")
    a6 = agent_by_sp_id(model, "6")
    assert not topology.G_school.has_edge(a1.unique_id, a6.unique_id), (
        "Agents 1 (SCH_1) and 6 (SCH_2) should not be connected in G_school."
    )


def test_agent_without_school_id_has_no_school_edges(model_and_topology):
    model, topology = model_and_topology
    a2 = agent_by_sp_id(model, "2")
    assert topology.G_school.degree(a2.unique_id) == 0


def test_school_graph_single_member_school_has_no_edges(model_and_topology):
    """Agent 6 is alone in SCH_2 and should have no edges."""
    model, topology = model_and_topology
    a6 = agent_by_sp_id(model, "6")
    assert topology.G_school.degree(a6.unique_id) == 0


# ------------------------------------------------------------------
# G_work integrity
# ------------------------------------------------------------------

def test_work_graph_connects_same_workplace(model_and_topology):
    model, topology = model_and_topology
    a2 = agent_by_sp_id(model, "2")
    a4 = agent_by_sp_id(model, "4")
    assert topology.G_work.has_edge(a2.unique_id, a4.unique_id), (
        "Agents 2 and 4 share WK_X but are not connected in G_work."
    )


def test_work_graph_does_not_cross_workplaces(model_and_topology):
    model, topology = model_and_topology
    a2 = agent_by_sp_id(model, "2")
    a5 = agent_by_sp_id(model, "5")
    assert not topology.G_work.has_edge(a2.unique_id, a5.unique_id), (
        "Agents 2 (WK_X) and 5 (WK_Y) should not be connected in G_work."
    )


def test_agent_without_work_id_has_no_work_edges(model_and_topology):
    model, topology = model_and_topology
    a1 = agent_by_sp_id(model, "1")
    assert topology.G_work.degree(a1.unique_id) == 0


# ------------------------------------------------------------------
# G_gq integrity
# ------------------------------------------------------------------

def test_gq_graph_connects_same_gq(model_and_topology):
    model, topology = model_and_topology
    a7 = agent_by_sp_id(model, "7")
    a8 = agent_by_sp_id(model, "8")
    assert topology.G_gq.has_edge(a7.unique_id, a8.unique_id), (
        "Agents 7 and 8 share GQ_Z but are not connected in G_gq."
    )


def test_agent_without_gq_id_has_no_gq_edges(model_and_topology):
    model, topology = model_and_topology
    a1 = agent_by_sp_id(model, "1")
    assert topology.G_gq.degree(a1.unique_id) == 0


# ------------------------------------------------------------------
# Node attribute: agent reference
# ------------------------------------------------------------------

def test_node_carries_agent_reference(model_and_topology):
    model, topology = model_and_topology
    for node_id, data in topology.G_home.nodes(data=True):
        assert "agent" in data, f"Node {node_id} is missing 'agent' attribute."
        assert data["agent"].unique_id == node_id


# ------------------------------------------------------------------
# Empty population
# ------------------------------------------------------------------

def test_empty_population_produces_empty_graphs():
    population = make_population()
    model = FluModel(population=population, seed=0)
    topology = model.topology
    assert topology.G_home.number_of_nodes() == 0
    assert topology.G_school.number_of_nodes() == 0
    assert topology.G_work.number_of_nodes() == 0
    assert topology.G_gq.number_of_nodes() == 0
