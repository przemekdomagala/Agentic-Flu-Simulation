"""
DataPreprocessor: Cluster-samples the RTI Synthetic Population dataset.

Responsibility: Load raw .txt files and produce a single simulation-ready
DataFrame by selecting intact household and group-quarter clusters.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


SENTINEL_MISSING = "X"


class DataPreprocessor:
    """Loads and cluster-samples the Philadelphia synthetic population dataset.

    The dataset is too large to load fully into memory, so this class
    performs cluster sampling: it selects a random subset of Household IDs
    and Group-Quarter (GQ) IDs, then extracts every person belonging to
    those clusters.  Household and GQ structures are kept intact — no
    household is partially represented in the output.
    """

    def __init__(self, dataset_dir: str | Path) -> None:
        self.dataset_dir = Path(dataset_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sample(
        self,
        n_households: int,
        n_gq: int,
        random_seed: int | None = None,
    ) -> pd.DataFrame:
        """Return a simulation-ready DataFrame of sampled individuals.

        Args:
            n_households: Number of household clusters to draw.
            n_gq: Number of group-quarter clusters to draw.
            random_seed: Optional seed for reproducible sampling.

        Returns:
            DataFrame with columns:
                sp_id, age, sex, sp_hh_id, school_id, work_id, sp_gq_id
            People from households have sp_gq_id = None.
            People from group quarters have sp_hh_id = None.
        """
        household_people = self._sample_households(n_households, random_seed)
        gq_people = self._sample_gq(n_gq, random_seed)

        combined = pd.concat([household_people, gq_people], ignore_index=True)
        combined = combined.drop_duplicates(subset="sp_id")
        return combined.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_tsv(self, filename: str) -> pd.DataFrame:
        return pd.read_csv(self.dataset_dir / filename, sep="\t", dtype=str)

    def _sample_households(
        self, n_households: int, random_seed: int | None
    ) -> pd.DataFrame:
        people = self._load_tsv("people.txt")
        households = self._load_tsv("households.txt")

        available_hh_ids = households["sp_id"].unique()
        rng = pd.Series(available_hh_ids).sample(
            n=min(n_households, len(available_hh_ids)),
            random_state=random_seed,
            replace=False,
        )
        selected_hh_ids = set(rng)

        sampled_people = people[people["sp_hh_id"].isin(selected_hh_ids)].copy()
        sampled_people = self._normalise_people_columns(sampled_people)
        sampled_people["sp_gq_id"] = None

        return sampled_people[
            ["sp_id", "age", "sex", "sp_hh_id", "school_id", "work_id", "sp_gq_id"]
        ]

    def _sample_gq(self, n_gq: int, random_seed: int | None) -> pd.DataFrame:
        gq_people = self._load_tsv("gq_people.txt")
        gq = self._load_tsv("gq.txt")

        available_gq_ids = gq["sp_id"].unique()
        rng = pd.Series(available_gq_ids).sample(
            n=min(n_gq, len(available_gq_ids)),
            random_state=random_seed,
            replace=False,
        )
        selected_gq_ids = set(rng)

        sampled_gq_people = gq_people[
            gq_people["sp_gq_id"].isin(selected_gq_ids)
        ].copy()

        sampled_gq_people["sp_hh_id"] = None
        sampled_gq_people["school_id"] = None
        sampled_gq_people["work_id"] = None

        return sampled_gq_people[
            ["sp_id", "age", "sex", "sp_hh_id", "school_id", "work_id", "sp_gq_id"]
        ]

    def _normalise_people_columns(self, people: pd.DataFrame) -> pd.DataFrame:
        """Replace sentinel 'X' values with None for school_id and work_id."""
        for column in ("school_id", "work_id"):
            people[column] = people[column].replace(SENTINEL_MISSING, None)
        return people
