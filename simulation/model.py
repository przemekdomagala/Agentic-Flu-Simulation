"""
FluModel: The top-level Mesa simulation model.

Responsibility: Initialise the agent population from a pre-processed
DataFrame and delegate network construction to TopologyBuilder.
All epidemiological logic belongs to Phase 2.
"""

from __future__ import annotations

import pandas as pd
import mesa

from simulation.agents import FluAgent
from simulation.topology import TopologyBuilder


class FluModel(mesa.Model):
    """Mesa model that initialises the flu simulation population.

    It expects a simulation-ready DataFrame produced by DataPreprocessor.
    Graph construction is delegated to TopologyBuilder so that this class
    remains focused on agent lifecycle management (Single Responsibility).

    Attributes:
        agents: All FluAgent instances (provided by Mesa internals).
        topology: A TopologyBuilder instance holding the four sub-graphs.
    """

    def __init__(
        self,
        population: pd.DataFrame,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)

        self._spawn_agents(population)
        self.topology = TopologyBuilder(list(self.agents))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _spawn_agents(self, population: pd.DataFrame) -> None:
        """Create one FluAgent per row in the population DataFrame."""
        for row in population.itertuples(index=False):
            FluAgent(
                model=self,
                sp_id=str(row.sp_id),
                age=self._parse_int(row.age),
                sex=str(row.sex),
                sp_hh_id=self._nullable_str(row.sp_hh_id),
                school_id=self._nullable_str(row.school_id),
                work_id=self._nullable_str(row.work_id),
                sp_gq_id=self._nullable_str(row.sp_gq_id),
            )

    @staticmethod
    def _parse_int(value: object) -> int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _nullable_str(value: object) -> str | None:
        if value is None:
            return None
        string_value = str(value)
        return None if string_value in ("None", "nan", "") else string_value
