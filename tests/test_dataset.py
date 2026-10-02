import pathlib
import pandas as pd
import pytest

DATASET_PATH = pathlib.Path("data/processed/dataset.parquet")

@pytest.fixture(scope="module")
def dataset():
    assert DATASET_PATH.exists(), "dataset.parquet must exist"
    return pd.read_parquet(DATASET_PATH)

def test_no_duplicate_zone_date(dataset):
    """Test there are no duplicate (zone, date) pairs."""
    dups = dataset.duplicated(subset=["zone", "date"]).sum()
    assert dups == 0, f"Found {dups} duplicate (zone, date) records."

def test_no_nan_labels(dataset):
    """Test that all label columns have zero NaN values."""
    assert dataset["label_danger"].isna().sum() == 0, "label_danger contains NaNs"
    assert dataset["label_warning"].isna().sum() == 0, "label_warning contains NaNs"

def test_sorted_dates(dataset):
    """Test that records are properly sorted by zone and date."""
    for zone, grp in dataset.groupby("zone"):
        dates = pd.to_datetime(grp["date"]).tolist()
        assert dates == sorted(dates), f"Dates in zone {zone} are not sorted in ascending order."

def test_join_example(dataset):
    """Test that a specific known date joins properly with expected weather columns."""
    sample = dataset[(dataset["station"] == "KALLOOPPARA") & (dataset["date"] == "2018-08-16")]
    assert len(sample) == 1, "Expected exactly 1 row for KALLOOPPARA on 2018-08-16"
    row = sample.iloc[0]
    assert row["precipitation_sum"] > 0, "Expected non-zero precipitation on 2018-08-16"
    assert row["daily_max"] >= 9.60, f"Expected daily_max near HFL (got {row['daily_max']})"

def test_exceedance_example_label_one(dataset):
    """Test that a known major flood date yields label 1 for both danger and warning."""
    # KALLOOPPARA 2018-08-16 had HFL of 9.64m (Danger=6.0m, Warning=5.0m)
    sample = dataset[(dataset["station"] == "KALLOOPPARA") & (dataset["date"] == "2018-08-16")]
    row = sample.iloc[0]
    assert row["label_danger"] == 1, "Expected label_danger == 1 for 2018-08-16 peak"
    assert row["label_warning"] == 1, "Expected label_warning == 1 for 2018-08-16 peak"

def test_dataset_columns(dataset):
    """Verify exact column structure and expected types."""
    expected = [
        "date", "zone", "station",
        "precipitation_sum", "rain_sum", "temperature_2m_max",
        "temperature_2m_min", "soil_moisture_0_7cm", "soil_moisture_7_28cm",
        "daily_max", "n_readings", "regime",
        "label_danger", "label_warning"
    ]
    assert list(dataset.columns) == expected
