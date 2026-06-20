"""
Unit tests for DataPreprocessor.

Tests verify:
- Cluster integrity: every person has a valid household or GQ ID.
- Output size is bounded by the clusters selected.
- Column schema is correct.
- Reproducibility with a fixed seed.
- Edge cases: requesting more clusters than available.
"""

from pathlib import Path

import pandas as pd
import pytest

from simulation.preprocessor import DataPreprocessor

DATASET_DIR = Path(__file__).parent.parent / "dataset"


@pytest.fixture(scope="module")
def preprocessor() -> DataPreprocessor:
    return DataPreprocessor(DATASET_DIR)


@pytest.fixture(scope="module")
def sampled(preprocessor: DataPreprocessor) -> pd.DataFrame:
    return preprocessor.sample(n_households=50, n_gq=5, random_seed=42)


# ------------------------------------------------------------------
# Schema
# ------------------------------------------------------------------

def test_output_has_required_columns(sampled: pd.DataFrame) -> None:
    expected_columns = {"sp_id", "age", "sex", "sp_hh_id", "school_id", "work_id", "sp_gq_id"}
    assert expected_columns.issubset(set(sampled.columns))


# ------------------------------------------------------------------
# Cluster integrity
# ------------------------------------------------------------------

def test_every_person_has_household_or_gq_id(sampled: pd.DataFrame) -> None:
    has_hh = sampled["sp_hh_id"].notna()
    has_gq = sampled["sp_gq_id"].notna()
    assert (has_hh | has_gq).all(), (
        "Some rows have neither sp_hh_id nor sp_gq_id - orphan records detected."
    )


def test_no_person_belongs_to_both_household_and_gq(sampled: pd.DataFrame) -> None:
    """Household people and GQ people are kept in separate groups."""
    both = sampled["sp_hh_id"].notna() & sampled["sp_gq_id"].notna()
    assert not both.any(), "A person cannot belong to both a household and a GQ."


def test_household_people_have_valid_hh_ids(preprocessor: DataPreprocessor) -> None:
    """sp_hh_id values in the output must exist in households.txt."""
    households = pd.read_csv(DATASET_DIR / "households.txt", sep="\t", dtype=str)
    valid_hh_ids = set(households["sp_id"])

    result = preprocessor.sample(n_households=30, n_gq=0, random_seed=1)
    hh_people = result[result["sp_hh_id"].notna()]

    invalid = ~hh_people["sp_hh_id"].isin(valid_hh_ids)
    assert not invalid.any(), "Output contains sp_hh_id values not found in households.txt."


def test_gq_people_have_valid_gq_ids(preprocessor: DataPreprocessor) -> None:
    """sp_gq_id values in the output must exist in gq.txt."""
    gq = pd.read_csv(DATASET_DIR / "gq.txt", sep="\t", dtype=str)
    valid_gq_ids = set(gq["sp_id"])

    result = preprocessor.sample(n_households=0, n_gq=3, random_seed=2)
    gq_people = result[result["sp_gq_id"].notna()]

    invalid = ~gq_people["sp_gq_id"].isin(valid_gq_ids)
    assert not invalid.any(), "Output contains sp_gq_id values not found in gq.txt."


# ------------------------------------------------------------------
# Output size
# ------------------------------------------------------------------

def test_output_is_non_empty(sampled: pd.DataFrame) -> None:
    assert len(sampled) > 0


def test_no_duplicate_individuals(sampled: pd.DataFrame) -> None:
    assert sampled["sp_id"].nunique() == len(sampled), "Duplicate sp_id entries found."


def test_gq_only_sample_has_no_household_people(preprocessor: DataPreprocessor) -> None:
    result = preprocessor.sample(n_households=0, n_gq=3, random_seed=7)
    assert result["sp_hh_id"].isna().all()


def test_household_only_sample_has_no_gq_people(preprocessor: DataPreprocessor) -> None:
    result = preprocessor.sample(n_households=20, n_gq=0, random_seed=7)
    assert result["sp_gq_id"].isna().all()


# ------------------------------------------------------------------
# Missing-value normalisation
# ------------------------------------------------------------------

def test_sentinel_x_replaced_with_none(preprocessor: DataPreprocessor) -> None:
    """'X' values from the raw dataset must not appear in the output."""
    result = preprocessor.sample(n_households=50, n_gq=0, random_seed=42)
    for column in ("school_id", "work_id"):
        assert "X" not in result[column].values, (
            f"Sentinel 'X' still present in column '{column}'."
        )


# ------------------------------------------------------------------
# Reproducibility
# ------------------------------------------------------------------

def test_same_seed_produces_identical_output(preprocessor: DataPreprocessor) -> None:
    df_a = preprocessor.sample(n_households=20, n_gq=2, random_seed=99)
    df_b = preprocessor.sample(n_households=20, n_gq=2, random_seed=99)
    pd.testing.assert_frame_equal(df_a, df_b)


def test_different_seeds_produce_different_output(preprocessor: DataPreprocessor) -> None:
    df_a = preprocessor.sample(n_households=20, n_gq=2, random_seed=1)
    df_b = preprocessor.sample(n_households=20, n_gq=2, random_seed=2)
    assert not df_a.equals(df_b)


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------

def test_requesting_more_households_than_available_does_not_crash(
    preprocessor: DataPreprocessor,
) -> None:
    result = preprocessor.sample(n_households=999_999, n_gq=0, random_seed=42)
    assert len(result) > 0


def test_requesting_more_gq_than_available_does_not_crash(
    preprocessor: DataPreprocessor,
) -> None:
    result = preprocessor.sample(n_households=0, n_gq=999_999, random_seed=42)
    assert len(result) > 0
