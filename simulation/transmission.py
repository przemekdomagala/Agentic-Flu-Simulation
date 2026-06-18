"""
Transmission mechanics: pure, injectable helper functions.

Responsibility: Calculate infection probability and determine whether a
single Susceptible-Infectious contact results in exposure.  All functions
are free of side effects so they can be tested in complete isolation, and
the caller (FluModel) is responsible for supplying the RNG sample.
"""

from __future__ import annotations

# Transmission multiplier per network layer.
# Keys match the location strings used by TopologyBuilder.
LOCATION_MULTIPLIERS: dict[str, float] = {
    "gq":        3.5,
    "home":      2.5,
    "school":    1.8,
    "work":      1.0,
    "community": 0.4,
}


def infection_probability(beta: float, location: str) -> float:
    """Return P(infection) for one Susceptible-Infectious edge contact.

    Args:
        beta:     Baseline transmissibility constant (calibrated externally).
        location: Network layer name; must be a key in LOCATION_MULTIPLIERS.

    Returns:
        Probability in [0, 1].

    Raises:
        KeyError: If *location* is not recognised.
    """
    return beta * LOCATION_MULTIPLIERS[location]


def exposure_occurred(beta: float, location: str, rng_sample: float) -> bool:
    """Determine whether a single contact event results in viral exposure.

    The caller is responsible for drawing *rng_sample* from a uniform
    distribution so this function remains a pure predicate and is fully
    testable without mocking random state.

    Args:
        beta:       Baseline transmissibility constant.
        location:   Network layer name.
        rng_sample: A uniform random float in [0, 1) drawn by the caller.

    Returns:
        True if the susceptible agent becomes exposed.
    """
    return rng_sample < infection_probability(beta, location)
