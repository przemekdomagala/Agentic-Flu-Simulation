"""
Phase 1 runner — demonstrates the full initialization pipeline.

Usage:
    python run_phase1.py [--households N] [--gq N] [--seed N]

This script does NOT run the epidemic simulation (that is Phase 2).
It shows that the population is correctly sampled, agents are created,
and all four network sub-graphs are built with proper topology.
"""

import argparse
import time
from pathlib import Path

from simulation.preprocessor import DataPreprocessor
from simulation.model import FluModel


DATASET_DIR = Path(__file__).parent / "dataset"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agentic Flu Simulation — Phase 1 initializer")
    parser.add_argument("--households", type=int, default=200,
                        help="Number of household clusters to sample (default: 200)")
    parser.add_argument("--gq", type=int, default=10,
                        help="Number of group-quarter clusters to sample (default: 10)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    return parser.parse_args()


def print_section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("  Agentic Flu Simulation — Phase 1: Infrastructure")
    print("=" * 60)
    print(f"  Dataset : {DATASET_DIR}")
    print(f"  Households to sample : {args.households}")
    print(f"  Group Quarters to sample : {args.gq}")
    print(f"  Random seed : {args.seed}")

    # ── Step 1: Preprocess ─────────────────────────────────────────
    print_section("Step 1 — Cluster Sampling (DataPreprocessor)")
    t0 = time.perf_counter()
    preprocessor = DataPreprocessor(DATASET_DIR)
    population = preprocessor.sample(
        n_households=args.households,
        n_gq=args.gq,
        random_seed=args.seed,
    )
    elapsed = time.perf_counter() - t0

    hh_people = population["sp_hh_id"].notna().sum()
    gq_people = population["sp_gq_id"].notna().sum()
    workers   = population["work_id"].notna().sum()
    students  = population["school_id"].notna().sum()

    print(f"  Sampling completed in {elapsed:.2f}s")
    print(f"  Total individuals   : {len(population):,}")
    print(f"  ├─ Household people : {hh_people:,}")
    print(f"  ├─ GQ residents     : {gq_people:,}")
    print(f"  ├─ Workers          : {workers:,}")
    print(f"  └─ Students         : {students:,}")

    # ── Step 2: Build agents & model ───────────────────────────────
    print_section("Step 2 — Agent Instantiation (FluModel)")
    t0 = time.perf_counter()
    model = FluModel(population=population, seed=args.seed)
    elapsed = time.perf_counter() - t0

    all_agents = list(model.agents)
    susceptible = sum(1 for a in all_agents if a.health_state.name == "SUSCEPTIBLE")

    print(f"  Model built in {elapsed:.2f}s")
    print(f"  Total agents created  : {len(all_agents):,}")
    print(f"  All in SUSCEPTIBLE state : {susceptible == len(all_agents)}")

    # ── Step 3: Network topology ────────────────────────────────────
    print_section("Step 3 — Network Topology (TopologyBuilder)")
    topology = model.topology

    graphs = {
        "G_home   (Household)": topology.G_home,
        "G_gq     (Group Quarters)": topology.G_gq,
        "G_work   (Workplace)": topology.G_work,
        "G_school (School)": topology.G_school,
    }

    for name, graph in graphs.items():
        nodes = graph.number_of_nodes()
        edges = graph.number_of_edges()
        isolated = sum(1 for n in graph.nodes if graph.degree(n) == 0)
        print(f"  {name}")
        print(f"    nodes={nodes:,}  edges={edges:,}  isolated (no group)={isolated:,}")

    # ── Summary ────────────────────────────────────────────────────
    print_section("Milestone 1 — Status")
    print("  Population sampled     : OK")
    print("  Agents initialised     : OK")
    print("  Network topology built : OK")
    print()
    print("  Phase 1 complete. Ready for professor review.")
    print("  Phase 2 will add the SEIR epidemic engine and time-stepped simulation.")
    print()


if __name__ == "__main__":
    main()
