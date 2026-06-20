"""
FluAgent: A single person in the flu simulation.

Responsibility: Store demographic attributes and drive the SEIR health-state
machine for one individual.  Routing, transmission, and telemetry are handled by FluModel.

Dependency Injection: the duration sampler callable is injected at construction
time so that tests can substitute a deterministic function without touching
Mesa's random state.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

import mesa

if TYPE_CHECKING:
    from simulation.model import FluModel

# ── SEIR phase parameters ────────────────────────────────────────────────────

_INCUBATION_MEAN: float = 48.0   # hours  (D_E ~ N(48, 12))
_INCUBATION_STD:  float = 12.0

_INFECTIOUS_MEAN: float = 168.0  # hours  (D_I ~ N(168, 24))
_INFECTIOUS_STD:  float = 24.0

_ELDERLY_AGE_THRESHOLD: int   = 65
_ELDERLY_PENALTY:       float = 0.20   # +20 % extension to D_I

_ASYMPTOMATIC_RATE: float = 0.35       # 35 % of infections are subclinical


def _clamp_positive(value: float) -> int:
    """Round a Gaussian draw to the nearest positive-integer tick count."""
    return max(1, round(value))


# ── Health-state enum ────────────────────────────────────────────────────────

class HealthState(Enum):
    SUSCEPTIBLE = auto()
    EXPOSED     = auto()
    INFECTIOUS  = auto()
    RECOVERED   = auto()


# ── Agent class ──────────────────────────────────────────────────────────────

class FluAgent(mesa.Agent):
    """An individual agent in the flu simulation.

    Demographic attributes come from the preprocessed population dataset.
    Fields not applicable to a particular individual (e.g. school_id for a
    working adult) are stored as None.

    SEIR mechanics
    ──────────────
    * Susceptible agents can be exposed via FluModel transmission logic.
    * Exposed agents advance a tick counter; when it reaches *state_duration*
      they become Infectious.
    * Infectious agents behave similarly and then move to Recovered.
    * Recovered agents are permanently immune.

    Duration sampling
    ─────────────────
    Phase durations are drawn from Gaussian distributions.  The sampler is
    injected via *duration_sampler* so unit tests can pass a deterministic
    stub (e.g. ``lambda mu, sigma: mu``) without touching global RNG state.
    When *duration_sampler* is None the model's own random.gauss is used.
    """

    def __init__(
        self,
        model: FluModel,
        sp_id: str,
        age: int,
        sex: str,
        sp_hh_id:   str | None,
        school_id:  str | None,
        work_id:    str | None,
        sp_gq_id:   str | None,
        duration_sampler: Callable[[float, float], float] | None = None,
    ) -> None:
        super().__init__(model)

        self.sp_id     = sp_id
        self.age       = age
        self.sex       = sex
        self.sp_hh_id  = sp_hh_id
        self.school_id = school_id
        self.work_id   = work_id
        self.sp_gq_id  = sp_gq_id

        self._sampler: Callable[[float, float], float] = (
            duration_sampler if duration_sampler is not None
            else model.random.gauss
        )

        self.health_state: HealthState = HealthState.SUSCEPTIBLE

        # Tick counters for the current phase
        self._ticks_in_state: int = 0
        self._state_duration: int = 0

        # Behavioural flags set during the infectious phase
        self.is_asymptomatic: bool = False
        self.is_quarantined:  bool = False  # locked to G_home when True

    # ── Public interface ──────────────────────────────────────────────────────

    def expose(self) -> None:
        """Transition S → E and sample the incubation duration.

        No-op if the agent is not currently Susceptible.
        Called by FluModel during transmission; agents never call this on
        themselves.
        """
        if self.health_state is not HealthState.SUSCEPTIBLE:
            return

        self.health_state = HealthState.EXPOSED
        self._ticks_in_state = 0
        raw_duration = self._sampler(_INCUBATION_MEAN, _INCUBATION_STD)
        self._state_duration = _clamp_positive(raw_duration)

    def step(self) -> None:
        """Advance the SEIR state machine by one tick.

        Susceptible and Recovered agents are stable; only Exposed and
        Infectious agents advance their phase counters.
        """
        if self.health_state in (HealthState.SUSCEPTIBLE, HealthState.RECOVERED):
            return

        self._ticks_in_state += 1

        if self.health_state is HealthState.EXPOSED:
            if self._ticks_in_state >= self._state_duration:
                self._transition_to_infectious()

        elif self.health_state is HealthState.INFECTIOUS:
            if self._ticks_in_state >= self._state_duration:
                self._transition_to_recovered()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _transition_to_infectious(self) -> None:
        self.health_state = HealthState.INFECTIOUS
        self._ticks_in_state = 0

        base_duration = self._sampler(_INFECTIOUS_MEAN, _INFECTIOUS_STD)
        if self.age > _ELDERLY_AGE_THRESHOLD:
            base_duration *= (1.0 + _ELDERLY_PENALTY)
        self._state_duration = _clamp_positive(base_duration)

        self.is_asymptomatic = self.model.random.random() < _ASYMPTOMATIC_RATE

    def _transition_to_recovered(self) -> None:
        self.health_state = HealthState.RECOVERED
        self._ticks_in_state = 0
        self._state_duration = 0
        self.is_quarantined  = False  # reset for any future re-use

    def __repr__(self) -> str:
        return (
            f"FluAgent(unique_id={self.unique_id}, sp_id={self.sp_id}, "
            f"age={self.age}, state={self.health_state.name})"
        )
