"""
FluAgent: A single person in the flu simulation.

Responsibility: Store demographic attributes and health state for one
individual.  All epidemic logic (state transitions, transmission) belongs
to Phase 2 and is intentionally absent here.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

import mesa

if TYPE_CHECKING:
    from simulation.model import FluModel


class HealthState(Enum):
    SUSCEPTIBLE = auto()
    EXPOSED = auto()
    INFECTIOUS = auto()
    RECOVERED = auto()


class FluAgent(mesa.Agent):
    """An individual agent in the flu simulation.

    Demographic attributes are sourced directly from the preprocessed
    population dataset.  Fields that are not applicable to a particular
    individual (e.g. school_id for a working adult) are stored as None.
    """

    def __init__(
        self,
        model: FluModel,
        sp_id: str,
        age: int,
        sex: str,
        sp_hh_id: str | None,
        school_id: str | None,
        work_id: str | None,
        sp_gq_id: str | None,
    ) -> None:
        super().__init__(model)

        self.sp_id = sp_id
        self.age = age
        self.sex = sex
        self.sp_hh_id = sp_hh_id
        self.school_id = school_id
        self.work_id = work_id
        self.sp_gq_id = sp_gq_id

        self.health_state: HealthState = HealthState.SUSCEPTIBLE

    def __repr__(self) -> str:
        return (
            f"FluAgent(unique_id={self.unique_id}, sp_id={self.sp_id}, "
            f"age={self.age}, state={self.health_state.name})"
        )
