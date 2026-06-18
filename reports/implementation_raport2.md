# Report - Engine, Behaviour & Telemetry
**Date:** 2026-06-18

---

## 1. Objective

This milestone brings the Phase 1 infrastructure to life. The simulation now runs a discrete hourly clock, propagates infection through a stochastic SEIR state machine, routes agents across time-filtered sub-graphs, and displays live telemetry in a browser dashboard. All Phase 2 tasks from `implementation_phase_2.md` are delivered.

---

## 2. Deliverables

### 2.1 Source Code

| File | Class / Module | Responsibility |
| :--- | :--- | :--- |
| `simulation/transmission.py` | `infection_probability`, `exposure_occurred` | Pure, injectable helpers that compute $P(\text{inf}) = \beta \times M_{\text{location}}$ and determine whether a contact results in exposure |
| `simulation/agents.py` | `FluAgent` | SEIR state machine (`step()`, `expose()`); injected `duration_sampler`; `is_asymptomatic` / `is_quarantined` behavioural flags |
| `simulation/model.py` | `FluModel` | Hourly clock, behavioural routing, transmission loop, absenteeism check, `DataCollector`, initial infection seeding |
| `simulation/topology.py` | `TopologyBuilder` | Added `G_community`; `active_base_graphs(hour)`; `rebuild_community_graph()` |
| `app.py` | `Page`, `SEIRChart`, `HotspotChart` | Solara browser dashboard — SEIR epidemic curve and transmission-hotspot bar chart |

### 2.2 Test Suite

| File | Tests | Scope |
| :--- | :---: | :--- |
| `tests/test_preprocessor.py` | 14 | Unchanged from Phase 1 |
| `tests/test_agents.py` | 10 | Unchanged from Phase 1 (fixture updated to `initial_infected=0`) |
| `tests/test_topology.py` | 19 | Unchanged from Phase 1 |
| `tests/test_seir.py` | 17 | Every SEIR transition, duration boundaries, elderly penalty, asymptomatic rate convergence, quarantine reset |
| `tests/test_transmission.py` | 25 | Every location multiplier, probability threshold, boundary conditions, `exposure_occurred` predicate |
| `tests/test_model.py` | 26 | Hourly routing, absenteeism compliance, quarantine edge logic, transmission with $\beta=0$ / $\beta=1$, `DataCollector` columns and row counts |
| **Total** | **111** | **111 passed, 0 failed** |

---

## 3. Step by Step Summary

### 3.1. Transmission Module (`simulation/transmission.py`)

A new, standalone module encapsulating all transmission mathematics. Decoupling this from the model follows the Single Responsibility Principle and makes every calculation independently testable without instantiating a Mesa model.

**Location multipliers:**

| Network Layer | $M_{\text{location}}$ |
| :--- | :---: |
| Group Quarters (`gq`) | 3.5 |
| Household (`home`) | 2.5 |
| School (`school`) | 1.8 |
| Workplace (`work`) | 1.0 |
| Community (`community`) | 0.4 |

**Key functions:**

- `infection_probability(beta, location)` — returns $\beta \times M_{\text{location}}$; raises `KeyError` for unknown locations.
- `exposure_occurred(beta, location, rng_sample)` — pure predicate; the caller supplies the uniform random draw so the function has no side effects and needs no mocking.

### 3.2. SEIR Engine (`simulation/agents.py`)

`FluAgent.step()` drives a four-state machine. Phase durations are drawn from Gaussian distributions using an injected `duration_sampler` callable, defaulting to `model.random.gauss`.

**State transitions:**

| Transition | Trigger | Duration |
| :--- | :--- | :--- |
| S → E | `expose()` called by `FluModel` | $D_E \sim \mathcal{N}(48, 12)$ h |
| E → I | `_ticks_in_state >= _state_duration` | $D_I \sim \mathcal{N}(168, 24)$ h |
| I → R | `_ticks_in_state >= _state_duration` | — |

**Vulnerability and behaviour flags:**
- If `age > 65`: $D_I$ extended by 20 %.
- On entering Infectious: `is_asymptomatic` set via a 35 % Bernoulli draw.
- On recovery: `is_quarantined` cleared automatically.

**Dependency injection:** passing `duration_sampler=lambda mu, sigma: mu` in tests freezes all durations to their mean values, enabling exact tick-by-tick assertions without touching any global RNG state.

### 3.3. Hourly Clock & Behavioural Routing (`simulation/model.py`, `simulation/topology.py`)

`FluModel.step()` implements a 1-tick = 1-hour loop with the following actions in order:

1. Reset per-tick `_infection_counts`.
2. **07:00 — absenteeism check:** 70 % of symptomatic Infectious agents have `is_quarantined` set to `True`, locking them to `G_home` for the day.
3. **16:00 — community rebuild:** `TopologyBuilder.rebuild_community_graph()` randomly selects 10 % of agents and connects them as a complete sub-graph in `G_community`.
4. **Transmission loop:** `_run_transmission(hour)` iterates every active edge.
5. **Agent step:** `agents.do("step")` advances each agent's SEIR counter.
6. **Telemetry:** `datacollector.collect(self)`.

**`TopologyBuilder.active_base_graphs(hour)`** returns the structurally active (graph, location) pairs:

| Hour range | Active layers |
| :--- | :--- |
| 00:00 – 08:00 | `G_home`, `G_gq` |
| 08:00 – 16:00 | `G_home`*, `G_gq`, `G_work`, `G_school` |
| 16:00 – 24:00 | `G_home`, `G_gq`, `G_community` |

\* `G_home` edges are skipped for agents with `work_id` or `school_id` during day hours via `_edge_is_active()`.

### 3.4. Transmission Mechanics

For every active edge, `FluModel._attempt_edge_transmission()` checks both directions:

```
if Infectious ↔ Susceptible:
    if random() < infection_probability(beta, location):
        susceptible.expose()
        _infection_counts[location] += 1
```

Quarantined agents skip all non-home, non-GQ edges. The `exposure_occurred()` helper from `transmission.py` is called with the caller-supplied random sample — no randomness is hidden inside the function.

### 3.5. Telemetry & Dashboard (`app.py`)

**`DataCollector`** is configured with nine model reporters collected at every tick:

| Reporter | Description |
| :--- | :--- |
| `Count_S/E/I/R` | Counts of agents in each SEIR state |
| `Infections_Home/GQ/Work/School/Community` | New exposures per network layer in the current tick |

**Solara dashboard** (`solara run app.py`) provides:

1. **SEIR Epidemic Curve** — live line chart; four colour-coded lines (S blue, E orange, I red, R green).
2. **Active Transmission Hotspots** — bar chart per network layer; reads the last completed row of the DataCollector so values always reflect a fully-processed tick; count labels above each bar.

---

## 4. Design Principles Compliance

| Principle | Implementation |
| :--- | :--- |
| **Single Responsibility** | `transmission.py` owns only math; `FluAgent` owns only SEIR; `FluModel` owns only orchestration; `TopologyBuilder` owns only graphs; `app.py` owns only the UI |
| **Open / Closed** | Adding a new graph layer requires only a new entry in `_HOUR_SCHEDULE` and one `_build_graph` call — no existing method changes |
| **Dependency Injection** | `duration_sampler` injected into `FluAgent`; RNG injected into `rebuild_community_graph()`; `beta` and `initial_infected` injectable on `FluModel` |
| **Clean Code** | No nested `if/else` in transmission; routing rules expressed as a single `_HOUR_SCHEDULE` dict; all risk calculations in named pure functions |
| **Testing** | Every viral transition, every probability check, every DataCollector method has a dedicated test; SEIR tests use a deterministic injected sampler — no full simulation required |

---

## 5. Runtime Results

Sample run (`n_households=200`, `n_gq=10`, `seed=42`, `initial_infected=5`):

```
Total agents         : 1,083
Initial exposed      : 5

G_home      nodes: 1,083   edges:     522
G_gq        nodes: 1,083   edges:  34,480
G_work      nodes: 1,083   edges:      43
G_school    nodes: 1,083   edges:     105
G_community nodes: 1,083   edges:       0  (rebuilt each evening tick)

Test suite: 111 passed, 0 failed  (25.3 s)
```

---

## 6. Test Quality Notes

- **SEIR tests** use `lambda mu, sigma: mu` as the injected sampler, making every state-transition tick-boundary exact and deterministic.
- **Transmission tests** are entirely pure; no Mesa model instantiation is needed since `infection_probability` and `exposure_occurred` take only scalars.
- **Model integration tests** use in-memory synthetic populations (5–200 agents) — no dataset I/O — and cover: tick progression, absenteeism compliance (statistical, ±10 %), quarantine routing, $\beta=0$ / $\beta=1$ edge cases, and DataCollector column/row assertions.
- All 43 Phase 1 tests continue to pass without modification (only the `small_model` fixture was updated to set `initial_infected=0`).

---

## 7. Next Steps

With Phase 2 complete, the simulation is functionally ready for final analysis:

1. **Calibration** — tune `beta` to achieve a target $R_0$ between 1.3 and 1.8 by running multi-seed sweeps and measuring the early exponential growth rate.
2. **Scenario analysis** — compare epidemic curves with and without absenteeism; vary `participation_rate` for the community layer.
3. **Report generation** — export `DataCollector` DataFrames to CSV / plots for the final academic report.
