"""
TopologyBuilder: Constructs the multi-layer NetworkX sub-graphs.

Responsibility: Build five distinct NetworkX graphs that encode structural
proximity, and resolve which graphs are active for a given hour of day.
Agent-level routing decisions (e.g. absenteeism, worker vs. student at home)
remain in FluModel to keep this class focused on graph construction only.

Sub-graphs
──────────
    G_home      - agents sharing the same household ID (sp_hh_id)
    G_gq        - agents sharing the same group-quarter ID (sp_gq_id)
    G_work      - agents sharing the same workplace ID (work_id)
    G_school    - agents sharing the same school ID (school_id)
    G_community - random sparse graph rebuilt each evening tick by FluModel

Each node in every graph is the agent's Mesa unique_id (integer).
Each node stores a reference to the agent object under the key "agent".
"""

from __future__ import annotations

import random as stdlib_random
from collections import defaultdict
from itertools import combinations
from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from simulation.agents import FluAgent


# ── Hourly activation schedule ────────────────────────────────────────────────
# Maps location name → (hour_start_inclusive, hour_end_exclusive).
# G_home spans the full day at the structural level; FluModel filters it
# per-agent during 08:00–16:00 for workers and students.
_HOUR_SCHEDULE: dict[str, tuple[int, int]] = {
    "home":      (0,  24),
    "gq":        (0,  24),
    "work":      (8,  16),
    "school":    (8,  16),
    "community": (16, 24),
}


class TopologyBuilder:
    """Builds and exposes the five social-network sub-graphs.

    All graphs except G_community are constructed eagerly at instantiation.
    G_community starts as an edgeless graph and is populated by
    ``rebuild_community_graph`` at the start of each evening tick.
    """

    def __init__(self, agents: list[FluAgent]) -> None:
        self.G_home:      nx.Graph = self._build_graph(agents, "sp_hh_id")
        self.G_gq:        nx.Graph = self._build_graph(agents, "sp_gq_id")
        self.G_work:      nx.Graph = self._build_graph(agents, "work_id")
        self.G_school:    nx.Graph = self._build_graph(agents, "school_id")
        self.G_community: nx.Graph = self._build_empty_graph(agents)

    # ── Public interface ──────────────────────────────────────────────────────

    def active_base_graphs(self, hour: int) -> list[tuple[nx.Graph, str]]:
        """Return (graph, location_name) pairs that are structurally active at *hour*.

        Note: G_home is included for all hours; it is FluModel's responsibility
        to skip home edges for mobile agents during 08:00–16:00.

        Args:
            hour: Current hour of day (0–23).

        Returns:
            Ordered list of (NetworkX graph, location string) tuples.
        """
        graph_map: dict[str, nx.Graph] = {
            "home":      self.G_home,
            "gq":        self.G_gq,
            "work":      self.G_work,
            "school":    self.G_school,
            "community": self.G_community,
        }
        return [
            (graph_map[name], name)
            for name, (start, end) in _HOUR_SCHEDULE.items()
            if start <= hour < end
        ]

    def rebuild_community_graph(
        self,
        agents: list[FluAgent],
        rng: stdlib_random.Random,
        participation_rate: float = 0.10,
    ) -> None:
        """Randomly regenerate G_community edges for one evening tick.

        Selects ``participation_rate`` fraction of all agents at random, then
        connects every pair among them (complete sub-graph on the sample).
        Existing edges are cleared first so the graph represents only the
        current tick's community contacts.

        Args:
            agents:             Full agent list.
            rng:                Seeded Random instance (injected by FluModel).
            participation_rate: Fraction of agents who venture into the
                                community; default 10 %.
        """
        self.G_community.remove_edges_from(list(self.G_community.edges()))

        n_participants = max(1, round(len(agents) * participation_rate))
        participants = rng.sample(agents, n_participants)

        for agent_a, agent_b in combinations(participants, 2):
            self.G_community.add_edge(agent_a.unique_id, agent_b.unique_id)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_graph(agents: list[FluAgent], group_attribute: str) -> nx.Graph:
        """Build an undirected graph connecting agents that share a group value.

        Args:
            agents:          All FluAgent instances in the simulation.
            group_attribute: Agent attribute used to cluster agents
                             (e.g. "sp_hh_id" for households).

        Returns:
            An undirected NetworkX Graph.  Nodes are agent unique_ids;
            the node attribute "agent" holds the FluAgent reference.
            Edges connect every pair of agents within the same cluster.
        """
        graph = nx.Graph()

        for agent in agents:
            graph.add_node(agent.unique_id, agent=agent)

        clusters: dict[str, list[FluAgent]] = defaultdict(list)
        for agent in agents:
            group_value = getattr(agent, group_attribute)
            if group_value is not None:
                clusters[group_value].append(agent)

        for members in clusters.values():
            for agent_a, agent_b in combinations(members, 2):
                graph.add_edge(agent_a.unique_id, agent_b.unique_id)

        return graph

    @staticmethod
    def _build_empty_graph(agents: list[FluAgent]) -> nx.Graph:
        """Build a node-only graph (no edges) for all agents."""
        graph = nx.Graph()
        for agent in agents:
            graph.add_node(agent.unique_id, agent=agent)
        return graph
