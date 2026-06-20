"""
Headless batch runner for What-If policy experiments.

Runs four scenarios entirely bypassing the Solara UI and writes one CSV
per scenario to the working directory.  Each CSV contains the full SEIR
and hotspot telemetry collected by Mesa's DataCollector.

Usage:
    python run_experiments.py
"""

from __future__ import annotations

from pathlib import Path

from simulation.model import FluModel
from simulation.preprocessor import DataPreprocessor

# ── Shared population sample (all scenarios use identical demographics) ────────

_DATASET_DIR = Path(__file__).parent / "dataset"
_N_HOUSEHOLDS = 200
_N_GQ         = 10
_RANDOM_SEED  = 42
_TICKS        = 1440   # 60 days × 24 hours


def _load_population():
    preprocessor = DataPreprocessor(_DATASET_DIR)
    return preprocessor.sample(
        n_households=_N_HOUSEHOLDS,
        n_gq=_N_GQ,
        random_seed=_RANDOM_SEED,
    )


def run_scenario(name: str, population, ticks: int = _TICKS, **kwargs) -> None:
    """Run one scenario, print progress, and save telemetry to a CSV.

    Args:
        name:       Short label used in the output filename.
        population: Pre-loaded population DataFrame (reused across scenarios).
        ticks:      Number of hourly simulation steps to run.
        **kwargs:   Any FluModel policy parameters to override the defaults.
    """
    print(f"\n{'─' * 60}")
    print(f"  Starting Scenario: {name}")
    print(f"{'─' * 60}")

    model = FluModel(population=population, seed=_RANDOM_SEED, **kwargs)

    for i in range(ticks):
        model.step()
        if i % 100 == 0:
            print(f"  [{name}] Tick {i}/{ticks} completed...")

    results = model.datacollector.get_model_vars_dataframe()
    filename = f"results_{name}.csv"
    results.to_csv(filename)
    print(f"  Saved → {filename}  ({len(results)} rows)")


if __name__ == "__main__":
    population = _load_population()
    print(f"Population loaded: {len(population):,} individuals")

    # 0. BASELINE — standard parameters (70 % compliance, open schools)
    run_scenario("Baseline", population)

    # 1. LOW COMPLIANCE — only 30 % stay home when sick (presenteeism)
    run_scenario("Low_Compliance", population, compliance_rate=0.30)

    # 2. SCHOOL CLOSURES — close schools once 2 % of population is infected
    run_scenario("School_Closures", population, school_closure_threshold=0.02)

    # 3. GQ LOCKDOWN — isolate nursing homes / dorms from community mixing
    run_scenario("GQ_Lockdown", population, gq_lockdown=True)

    print("\n" + "=" * 60)
    print("  All experiments successfully completed!")
    print("  Output files:")
    for name in ("Baseline", "Low_Compliance", "School_Closures", "GQ_Lockdown"):
        print(f"    results_{name}.csv")
    print("=" * 60)
