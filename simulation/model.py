"""
FluModel: Top-level Mesa simulation model.

Responsibility: Orchestrate the simulation clock, behavioural routing,
transmission mechanics, agent lifecycle management, and telemetry collection.

Epidemiological state transitions live in FluAgent.
Transmission probability helpers live in transmission.py.
Graph construction lives in TopologyBuilder.ss
"""

from __future__ import annotations

import pandas as pd
import mesa

from simulation.agents import FluAgent, HealthState
from simulation.topology import TopologyBuilder
from simulation.transmission import exposure_occurred

# ── Model-level constants ─────────────────────────────────────────────────────

_BETA: float              = 0.04   # baseline transmissibility (calibrated for R₀ ≈ 1.3-1.8)
_INITIAL_INFECTED: int    = 5
_ABSENTEEISM_HOUR: int    = 7      # 07:00 compliance check
_ABSENTEEISM_RATE: float  = 0.70   # 70 % of symptomatic agents quarantine
_COMMUNITY_HOUR:   int    = 16     # G_community rebuilt each evening


class FluModel(mesa.Model):
    """Mesa model that drives the Philadelphia flu epidemic simulation.

    Each call to ``step()`` advances the clock by one hour and performs:
      1. Absenteeism check at 07:00
      2. Community graph rebuild at 16:00
      3. Transmission across all active network edges
      4. Agent SEIR state progression
      5. Telemetry collection

    Attributes:
        tick:          Current simulation tick (0-based; 1 tick = 1 hour).
        topology:      TopologyBuilder holding all five sub-graphs.
        datacollector: Mesa DataCollector for SEIR and hotspot telemetry.
        beta:          Baseline transmissibility constant.
    """

    def __init__(
        self,
        population: pd.DataFrame,
        seed: int | None = None,
        beta: float = _BETA,
        initial_infected: int = _INITIAL_INFECTED,
        compliance_rate: float = _ABSENTEEISM_RATE,
        school_closure_threshold: float | None = None,
        gq_lockdown: bool = False,
    ) -> None:
        super().__init__(seed=seed)

        self.beta: float = beta
        self.tick: int   = 0

        # Policy parameters
        self.compliance_rate: float               = compliance_rate
        self.school_closure_threshold: float | None = school_closure_threshold
        self.gq_lockdown: bool                    = gq_lockdown
        self.schools_open: bool                   = True

        # Per-tick infection source tallies (reset at the top of each step)
        self._infection_counts: dict[str, int] = {
            loc: 0 for loc in ("home", "gq", "work", "school", "community")
        }

        self._spawn_agents(population)
        self.num_agents: int = len(list(self.agents))
        self.topology = TopologyBuilder(list(self.agents))
        self._seed_infections(initial_infected)
        self._setup_datacollector()

        # Collect initial state so the dashboard shows tick-0 data immediately
        self.datacollector.collect(self)

    # ── Mesa interface ────────────────────────────────────────────────────────

    def step(self) -> None:
        """Advance the simulation by one hour (one tick)."""
        hour = self.tick % 24

        self._reset_infection_counts()

        # Dynamic school closure: check once per tick until threshold is crossed
        if self.school_closure_threshold is not None and self.schools_open:
            active_cases = sum(
                1 for a in self.agents
                if a.health_state in (HealthState.EXPOSED, HealthState.INFECTIOUS)
            )
            if active_cases / self.num_agents >= self.school_closure_threshold:
                self.schools_open = False
                print(f"Tick {self.tick}: Outbreak threshold reached. Schools CLOSED.")

        if hour == _ABSENTEEISM_HOUR:
            self._apply_absenteeism()

        if hour == _COMMUNITY_HOUR:
            # GQ lockdown: exclude group-quarter residents from community mixing
            community_agents = (
                [a for a in self.agents if a.sp_gq_id is None]
                if self.gq_lockdown
                else list(self.agents)
            )
            self.topology.rebuild_community_graph(community_agents, self.random)

        self._run_transmission(hour)
        self.agents.do("step")
        self.datacollector.collect(self)

        self.tick += 1

    # ── Private: initialisation ───────────────────────────────────────────────

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

    def _seed_infections(self, n: int) -> None:
        """Expose *n* randomly chosen agents to start the outbreak."""
        all_agents = list(self.agents)
        seeds = self.random.sample(all_agents, min(n, len(all_agents)))
        for agent in seeds:
            agent.expose()

    def _setup_datacollector(self) -> None:
        """Configure Mesa DataCollector for SEIR counts and hotspot tallies.

        SEIR reporters are decoupled from transmission logic via lambdas;
        hotspot reporters read the per-tick ``_infection_counts`` dict that
        is reset at the start of each step.
        """
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Count_S": lambda m: _count_state(m, HealthState.SUSCEPTIBLE),
                "Count_E": lambda m: _count_state(m, HealthState.EXPOSED),
                "Count_I": lambda m: _count_state(m, HealthState.INFECTIOUS),
                "Count_R": lambda m: _count_state(m, HealthState.RECOVERED),
                "Infections_Home":      lambda m: m._infection_counts["home"],
                "Infections_GQ":        lambda m: m._infection_counts["gq"],
                "Infections_Work":      lambda m: m._infection_counts["work"],
                "Infections_School":    lambda m: m._infection_counts["school"],
                "Infections_Community": lambda m: m._infection_counts["community"],
            }
        )

    # ── Private: clock logic ──────────────────────────────────────────────────

    def _reset_infection_counts(self) -> None:
        for key in self._infection_counts:
            self._infection_counts[key] = 0

    def _apply_absenteeism(self) -> None:
        """At 07:00, flag symptomatic Infectious agents for quarantine.

        ``compliance_rate`` % of symptomatic agents suspend G_work / G_school
        routing and stay locked to G_home for the day.  Asymptomatic agents
        are never flagged (they do not know they are infectious).
        """
        for agent in self.agents:
            if (
                agent.health_state is HealthState.INFECTIOUS
                and not agent.is_asymptomatic
                and self.random.random() < self.compliance_rate
            ):
                agent.is_quarantined = True

    def _run_transmission(self, hour: int) -> None:
        """Attempt transmission on every active edge for the current hour."""
        for graph, location in self.topology.active_base_graphs(hour):
            if location == "school" and not self.schools_open:
                continue
            for uid_a, uid_b in graph.edges():
                agent_a: FluAgent = graph.nodes[uid_a]["agent"]
                agent_b: FluAgent = graph.nodes[uid_b]["agent"]

                if not self._edge_is_active(agent_a, agent_b, location, hour):
                    continue

                self._attempt_edge_transmission(agent_a, agent_b, location)

    def _edge_is_active(
        self,
        agent_a: FluAgent,
        agent_b: FluAgent,
        location: str,
        hour: int,
    ) -> bool:
        """Return False when this edge should be skipped for this tick.

        Two rules:
        1. During work/school hours (08:00-16:00), home edges are inactive for
           agents who have work or school obligations (they are elsewhere).
        2. Quarantined agents skip all non-home, non-GQ edges.
        """
        if location == "home" and 8 <= hour < 16:
            if _is_mobile(agent_a) or _is_mobile(agent_b):
                return False

        if location not in ("home", "gq"):
            if agent_a.is_quarantined or agent_b.is_quarantined:
                return False

        return True

    def _attempt_edge_transmission(
        self,
        agent_a: FluAgent,
        agent_b: FluAgent,
        location: str,
    ) -> None:
        """Try to transmit infection along one undirected edge (both directions).

        Transmission is checked in both directions so a single edge can
        infect at most one new Susceptible per tick (the first direction that
        succeeds does not prevent checking the other, but an already-exposed
        agent's ``expose()`` call is a no-op).
        """
        for infectious, susceptible in ((agent_a, agent_b), (agent_b, agent_a)):
            if (
                infectious.health_state is HealthState.INFECTIOUS
                and susceptible.health_state is HealthState.SUSCEPTIBLE
            ):
                rng_sample = self.random.random()
                if exposure_occurred(self.beta, location, rng_sample):
                    susceptible.expose()
                    self._infection_counts[location] += 1

    # ── Private: static helpers ───────────────────────────────────────────────

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


# ── Module-level helpers (no access to self needed; easier to test) ───────────

def _count_state(model: FluModel, state: HealthState) -> int:
    """Count agents in a given HealthState."""
    return sum(1 for a in model.agents if a.health_state is state)


def _is_mobile(agent: FluAgent) -> bool:
    """Return True if the agent has work or school obligations during day hours."""
    return agent.work_id is not None or agent.school_id is not None
