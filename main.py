import argparse
import time
from pathlib import Path

from simulation.preprocessor import DataPreprocessor
from simulation.model import FluModel


DATASET_DIR = Path(__file__).parent / "dataset"


def print_section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def main() -> None:

    print("=" * 60)
    print("  Agentic Flu Simulation - Infrastructure")
    print("=" * 60)
    print(f"  Dataset : {DATASET_DIR}")

    # ── Step 1: Preprocess ─────────────────────────────────────────
    print_section("Step 1 - Cluster Sampling (DataPreprocessor)")
    t0 = time.perf_counter()
    preprocessor = DataPreprocessor(DATASET_DIR)
    population = preprocessor.sample(
        n_households=200,
        n_gq=10,
        random_seed=42,
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
    print_section("Step 2 - Agent Instantiation (FluModel)")
    t0 = time.perf_counter()
    model = FluModel(population=population, seed=42)
    elapsed = time.perf_counter() - t0

    all_agents = list(model.agents)
    susceptible = sum(1 for a in all_agents if a.health_state.name == "SUSCEPTIBLE")

    print(f"  Model built in {elapsed:.2f}s")
    print(f"  Total agents created  : {len(all_agents):,}")
    print(f"  All in SUSCEPTIBLE state : {susceptible == len(all_agents)}")

    # ── Step 3: Network topology ────────────────────────────────────
    print_section("Step 3 - Network Topology (TopologyBuilder)")
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
    print_section("Status")
    print("  Population sampled     : OK")
    print("  Agents initialised     : OK")
    print("  Network topology built : OK")
    print()


if __name__ == "__main__":
    main()
