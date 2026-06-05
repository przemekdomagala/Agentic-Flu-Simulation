"""
TopologyBuilder: Constructs the multi-layer NetworkX sub-graphs.

Responsibility: Given a list of FluAgent instances, build four distinct
NetworkX graphs that encode structural proximity.  Time-filtering logic
(activating/deactivating sub-graphs by hour of day) belongs to Phase 2.

Sub-graphs:
    G_home   — agents sharing the same Household ID (sp_hh_id)
    G_gq     — agents sharing the same Group-Quarter ID (sp_gq_id)
    G_work   — agents sharing the same Work ID (work_id)
    G_school — agents sharing the same School ID (school_id)

Each node in every graph is the agent's Mesa unique_id (integer).
Each node also stores a reference to the agent object for convenience.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from simulation.agents import FluAgent


class TopologyBuilder:
    """Builds and exposes the four social-network sub-graphs.

    All four graphs are constructed eagerly at instantiation time so that
    the model can start querying them immediately after __init__ completes.
    """

    def __init__(self, agents: list[FluAgent]) -> None:
        self.G_home: nx.Graph = self._build_graph(agents, "sp_hh_id")
        self.G_gq: nx.Graph = self._build_graph(agents, "sp_gq_id")
        self.G_work: nx.Graph = self._build_graph(agents, "work_id")
        self.G_school: nx.Graph = self._build_graph(agents, "school_id")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_graph(agents: list[FluAgent], group_attribute: str) -> nx.Graph:
        """Build an undirected graph connecting agents that share a group value.

        Args:
            agents: All FluAgent instances in the simulation.
            group_attribute: The agent attribute name used to cluster agents
                (e.g. "sp_hh_id" for households).

        Returns:
            An undirected NetworkX Graph.  Nodes are agent unique_ids;
            node attribute "agent" holds the FluAgent reference.
            Edges connect every pair of agents within the same cluster.
        """
        graph = nx.Graph()

        # Register all agents as nodes regardless of whether they belong
        # to any cluster, so the graph is always fully populated.
        for agent in agents:
            graph.add_node(agent.unique_id, agent=agent)

        # Group agents by their shared attribute value.
        clusters: dict[str, list[FluAgent]] = defaultdict(list)
        for agent in agents:
            group_value = getattr(agent, group_attribute)
            if group_value is not None:
                clusters[group_value].append(agent)

        # Connect every pair within each cluster (complete sub-graph per group).
        for members in clusters.values():
            for agent_a, agent_b in combinations(members, 2):
                graph.add_edge(agent_a.unique_id, agent_b.unique_id)

        return graph
