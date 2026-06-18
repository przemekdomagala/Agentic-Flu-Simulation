"""
Flu Simulation Dashboard — direct Solara page.

Run with:
    .venv/bin/python3 -m solara run app.py
"""

from __future__ import annotations

import matplotlib
from pathlib import Path

import solara
from matplotlib.figure import Figure
from mesa.visualization.solara_viz import ModelController, update_counter

from simulation.model import FluModel
from simulation.preprocessor import DataPreprocessor

# ── Build the initial model ───────────────────────────────────────────────────

_DATASET_DIR = Path(__file__).parent / "dataset"
_preprocessor = DataPreprocessor(_DATASET_DIR)
_population   = _preprocessor.sample(n_households=200, n_gq=10, random_seed=42)
_MODEL_PARAMS = {"population": _population, "seed": 42}

# ── Constants ─────────────────────────────────────────────────────────────────

_SEIR_COLORS = {
    "Count_S": "#2196F3",
    "Count_E": "#FF9800",
    "Count_I": "#F44336",
    "Count_R": "#4CAF50",
}

_HOTSPOT_COLS   = ["Infections_Home", "Infections_GQ",    "Infections_Work",
                   "Infections_School", "Infections_Community"]
_HOTSPOT_LABELS = ["Home",            "GQ",               "Work",
                   "School",          "Community"]
_HOTSPOT_COLORS = ["#E91E63",         "#9C27B0",           "#2196F3",
                   "#009688",         "#FF5722"]

# ── Chart components ──────────────────────────────────────────────────────────

@solara.component
def SEIRChart(model: FluModel) -> None:
    """Live SEIR epidemic curve — one line per health state."""
    update_counter.get()

    df = model.datacollector.get_model_vars_dataframe()

    fig = Figure(figsize=(7, 4))
    ax  = fig.subplots()
    for col, color in _SEIR_COLORS.items():
        if col in df.columns:
            ax.plot(df[col], label=col.replace("Count_", ""), color=color, linewidth=1.8)
    ax.set_xlabel("Tick (hours)")
    ax.set_ylabel("Agents")
    ax.set_title("SEIR Epidemic Curve")
    ax.legend(loc="upper right", fontsize=8)
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    fig.tight_layout()
    solara.FigureMatplotlib(fig, format="png")


@solara.component
def HotspotChart(model: FluModel) -> None:
    """Bar chart — infections per network layer from the last completed tick."""
    update_counter.get()

    df = model.datacollector.get_model_vars_dataframe()
    if df.empty:
        counts = [0] * len(_HOTSPOT_LABELS)
    else:
        last   = df.iloc[-1]
        counts = [int(last.get(col, 0)) for col in _HOTSPOT_COLS]

    fig = Figure(figsize=(7, 4))
    ax  = fig.subplots()
    bars = ax.bar(_HOTSPOT_LABELS, counts, color=_HOTSPOT_COLORS, edgecolor="white")
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xlabel("Network Layer")
    ax.set_ylabel("New Infections")
    ax.set_title("Active Transmission Hotspots (Last Completed Tick)")
    ax.set_ylim(bottom=0, top=max(max(counts) * 1.25, 1))
    fig.tight_layout()
    solara.FigureMatplotlib(fig, format="png")


@solara.component
def StatusLine(model: FluModel) -> None:
    """Tick / hour / day counter — refreshes on every model step."""
    update_counter.get()
    hour = model.tick % 24
    day  = model.tick // 24 + 1
    solara.Text(f"Tick: {model.tick}   |   Hour: {hour:02d}:00   |   Day: {day}")


# ── Main page ─────────────────────────────────────────────────────────────────

@solara.component
def Page() -> None:
    model_reactive = solara.use_reactive(FluModel(**_MODEL_PARAMS))

    with solara.AppBar():
        solara.AppBarTitle("Philadelphia Flu Simulation")

    with solara.Column(style="padding: 16px; width: 100%;"):

        # ── Top control bar ───────────────────────────────────────────────────
        with solara.Card(style="margin-bottom: 12px;"):
            with solara.Row(style="align-items: center; flex-wrap: wrap; gap: 16px;"):
                with solara.Column(style="flex: 0 0 auto;"):
                    ModelController(
                        model_reactive,
                        model_parameters=_MODEL_PARAMS,
                        play_interval=150,
                    )
                with solara.Column(style="flex: 1 1 auto; justify-content: center;"):
                    StatusLine(model_reactive.value)

        # ── Charts row ────────────────────────────────────────────────────────
        with solara.Row(style="flex-wrap: wrap; gap: 16px; align-items: flex-start;"):
            with solara.Column(style="flex: 1; min-width: 380px;"):
                SEIRChart(model_reactive.value)
            with solara.Column(style="flex: 1; min-width: 380px;"):
                HotspotChart(model_reactive.value)


page = Page()
