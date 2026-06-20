# Agentic Flu Simulation

An agent-based model of influenza spread across a synthetic Philadelphia population. Each person is represented as an autonomous agent following a SEIR health-state machine, embedded in a multi-layer contact network (household, workplace, school, group quarters, community).

Built with [Mesa 3](https://mesa.readthedocs.io/) and visualised with [Solara](https://solara.dev/).

---

## Project structure

```
Agentic-Flu-Simulation/
├── simulation/
│   ├── agents.py        # FluAgent - SEIR state machine per individual
│   ├── model.py         # FluModel - simulation clock, transmission, telemetry
│   ├── topology.py      # TopologyBuilder - five-layer contact network (NetworkX)
│   ├── transmission.py  # Pure transmission-probability helpers
│   └── preprocessor.py  # DataPreprocessor - cluster-sample the population dataset
├── tests/               # pytest test suite
├── dataset/             # Raw synthetic population files (people, households, GQ)
├── docs/                # Design documentation and implementation reports
├── results/             # Pre-generated experiment CSVs
├── app.py               # Solara interactive dashboard
├── main.py              # Infrastructure smoke-test / quick-start script
├── run_experiments.py   # Headless batch runner for what-if scenarios
├── requirements.txt
└── pytest.ini
```

---

## Epidemiological model

### SEIR states

| State | Description |
|-------|-------------|
| **S** - Susceptible | Healthy; can be exposed via contact |
| **E** - Exposed | Infected but not yet infectious (incubation ~48 h, σ = 12 h) |
| **I** - Infectious | Actively spreading; duration ~168 h (σ = 24 h), +20 % for agents aged 65+ |
| **R** - Recovered | Permanently immune |

35 % of infectious agents are asymptomatic and never quarantine.

### Contact network layers

Transmission is simulated across five network layers with location-specific multipliers applied to the baseline transmissibility `β = 0.04` (calibrated for R₀ ≈ 1.3-1.8):

| Layer | Multiplier | Active hours |
|-------|-----------|--------------|
| Group Quarters (GQ) | 3.5× | 24 h |
| Household | 2.5× | outside work/school hours |
| School | 1.8× | 08:00-16:00 |
| Workplace | 1.0× | 08:00-16:00 |
| Community | 0.4× | rebuilt daily at 16:00 |

### Behavioural policies

Each `FluModel` instance accepts the following policy parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `compliance_rate` | 0.70 | Fraction of symptomatic agents who quarantine at home |
| `school_closure_threshold` | `None` | Fraction of population infected that triggers school closure |
| `gq_lockdown` | `False` | Exclude GQ residents from community mixing |

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Running

### Interactive dashboard

```bash
python -m solara run app.py
```

Opens a live Solara dashboard with a SEIR epidemic curve and a hotspot bar chart showing new infections per network layer each tick.

### Infrastructure smoke-test

```bash
python main.py
```

Samples the population, builds agents, and reports network topology statistics. No simulation steps are run.

### Batch what-if experiments

```bash
python run_experiments.py
```

Runs four headless scenarios (1 440 ticks = 60 days) and writes one CSV per scenario to the working directory:

| Scenario | Description |
|----------|-------------|
| `results_Baseline.csv` | Default parameters (70 % compliance, schools open) |
| `results_Low_Compliance.csv` | 30 % compliance (presenteeism) |
| `results_School_Closures.csv` | Schools close once 2 % of population is infected |
| `results_GQ_Lockdown.csv` | GQ residents excluded from community mixing |

Each CSV contains per-tick SEIR counts and per-layer infection tallies collected by Mesa's `DataCollector`.

### Tests

```bash
pytest
```

---

## Dataset

Synthetic population files derived from the RTI SYNTH-POP dataset for Philadelphia. The `DataPreprocessor` performs cluster sampling:

- `n_households` households drawn at random
- `n_gq` group-quarter facilities drawn at random
- All residents of the selected households/GQ units are included

Default sample: 200 households + 10 GQ facilities, seed 42.
