# Report - Infrastructure & Topology  
**Date:** 2026-06-05  

---

## 1. Objective

This part establishes the core infrastructure required to run the simulation: a population data pipeline, an agent framework, and a multi-layer social network topology. No epidemic logic is included in this milestone.

---

## 2. Deliverables

### 2.1 Source Code

| File | Class | Responsibility |
| :--- | :--- | :--- |
| `simulation/preprocessor.py` | `DataPreprocessor` | Reads raw `.txt` dataset files and produces a simulation-ready DataFrame via cluster sampling |
| `simulation/agents.py` | `FluAgent`, `HealthState` | Represents a single individual; holds demographic attributes and initial health state |
| `simulation/model.py` | `FluModel` | Top-level Mesa model; spawns agents from a DataFrame and delegates graph construction |
| `simulation/topology.py` | `TopologyBuilder` | Builds the four social sub-graphs (`G_home`, `G_gq`, `G_work`, `G_school`) using NetworkX |
| `main.py` | - | Entry-point script; runs the full pipeline and prints a diagnostic summary |

### 2.2 Test Suite

| File | Tests | Scope |
| :--- | :---: | :--- |
| `tests/test_preprocessor.py` | 14 | Cluster integrity, schema, sentinel normalisation, reproducibility, edge cases |
| `tests/test_agents.py` | 10 | Agent count, attribute mapping, initial health state, unique IDs, determinism |
| `tests/test_topology.py` | 19 | Intra-group connectivity, cross-group isolation, node references, empty population |
| **Total** | **43** | **43 passed, 0 failed** |

---

## 3. Step by Step Summary

### 3.1. Data Preprocessor (Cluster Sampling)

**Class:** `DataPreprocessor`  
**Input files:** `people.txt` (~1.46 M rows), `households.txt` (~600 K rows), `gq.txt` (183 rows), `gq_people.txt` (~44 K rows)

The preprocessor implements the cluster sampling algorithm described in the design documentation:

1. Randomly selects `n_households` Household IDs from `households.txt`.
2. Extracts every individual in `people.txt` whose `sp_hh_id` matches a selected household.
3. Randomly selects `n_gq` Group Quarter IDs from `gq.txt`.
4. Extracts every individual in `gq_people.txt` whose `sp_gq_id` matches a selected GQ.
5. Merges both sets, removes duplicates, and returns a single DataFrame.

Sentinel values (`"X"`) for `school_id` and `work_id` are normalised to `None` at this boundary so that no downstream component needs to handle raw dataset artefacts.

The output schema is:

| Column | Description |
| :--- | :--- |
| `sp_id` | Synthetic person ID |
| `age` | Age in years |
| `sex` | `M` / `F` |
| `sp_hh_id` | Household ID (`None` for GQ residents) |
| `school_id` | School ID (`None` if not a student) |
| `work_id` | Workplace ID (`None` if not employed) |
| `sp_gq_id` | Group Quarter ID (`None` for household residents) |

### 3.2. Core Mesa Setup

**Classes:** `FluAgent`, `FluModel`

`FluAgent` extends `mesa.Agent`. It stores all seven demographic attributes and initialises `health_state` to `HealthState.SUSCEPTIBLE`. Mesa auto-assigns a `unique_id` integer to each agent upon registration.

`FluModel` extends `mesa.Model`. It accepts a pre-processed DataFrame (keeping file I/O decoupled from the simulation core) and iterates over its rows to create one `FluAgent` per person. After population creation it hands off all agents to `TopologyBuilder`.

### 3.3. Network Topology

**Class:** `TopologyBuilder`

Four undirected NetworkX graphs are built eagerly at model initialisation:

| Sub-graph | Clustering attribute | Activation window (Next Milestone) |
| :--- | :--- | :--- |
| `G_home` | `sp_hh_id` | 00:00–08:00 and 16:00–24:00 |
| `G_gq` | `sp_gq_id` | 00:00–24:00 (always active) |
| `G_work` | `work_id` | 08:00–16:00 |
| `G_school` | `school_id` | 08:00–16:00 |

Each graph contains all agents as nodes (so degree queries are always valid). Edges are drawn using a complete sub-graph per cluster: every pair of agents sharing the same attribute value receives a direct edge. Agents with `None` for a given attribute have no edges in that sub-graph. Every node stores an `"agent"` attribute holding a direct reference to the `FluAgent` object.

---

## 4. Runtime Results

Sample run with `--households 200 --gq 10 --seed 42`:

```
Total individuals   : 1,083
├─ Household people : 481
├─ GQ residents     : 602
├─ Workers          : 190
└─ Students         : 98

Sampling time       : 1.74 s
Agent creation time : 0.09 s

G_home   - nodes: 1,083  edges:     522
G_gq     - nodes: 1,083  edges:  34,480
G_work   - nodes: 1,083  edges:      43
G_school - nodes: 1,083  edges:     105
```

The high edge count in `G_gq` reflects the dense nature of group-quarter clusters (nursing homes, dormitories), consistent with the design documentation's maximum transmission multiplier of 3.5 assigned to that layer.

---


## 6. Test Quality Notes

- Tests are completely independent of each other (no shared mutable state).
- Preprocessor tests hit the real dataset files to validate end-to-end cluster integrity.
- Agent and topology tests use in-memory synthetic populations so they run in milliseconds.

---

## 7. Next Steps

For the next milestone, we'll implement:

1. **SEIR state machine** - stochastic transitions driven by Gaussian-distributed phase durations ($D_E \sim \mathcal{N}(48, 12)$ h, $D_I \sim \mathcal{N}(168, 24)$ h).
2. **Transmission engine** - per-tick exposure checks on active sub-graph edges using $P(\text{inf}) = \beta \times M_{\text{location}}$.
3. **Hourly time-step loop** - time-filtered sub-graph activation/deactivation; symptom-driven absenteeism at 07:00.
4. **Telemetry dashboard** - live SEIR epidemic curve and transmission-vector bar chart via Mesa's visualization modules.
