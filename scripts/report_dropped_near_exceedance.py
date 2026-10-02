import pathlib
from datetime import timedelta
import pandas as pd

out_dir = pathlib.Path("docs/step0")
out_dir.mkdir(parents=True, exist_ok=True)

PROCESSED_DIR = pathlib.Path("data/processed")
ds_df = pd.read_parquet(PROCESSED_DIR / "dataset.parquet")
ds_df["date"] = pd.to_datetime(ds_df["date"])

# Load raw labels
labels_raw = pd.read_csv(PROCESSED_DIR / "labels_daily.csv")
labels_raw["date"] = pd.to_datetime(labels_raw["date"]).dt.date

# 1. Exceedances in dataset
exceed_df = ds_df[(ds_df["label_danger"] == 1) | (ds_df["label_warning"] == 1)][
    ["date", "zone", "station", "label_warning", "label_danger", "daily_max"]
].sort_values("date").reset_index(drop=True)

# 2. Missing days in raw labels
missing_days = labels_raw[labels_raw["label_warning"].isna()][["date", "station"]].drop_duplicates().sort_values("date").reset_index(drop=True)

# 3. Near Exceedance Pairs
pairs = []
for _, ex_row in exceed_df.iterrows():
    ex_d = ex_row["date"].date()
    stn = ex_row["station"]
    z = ex_row["zone"]
    for offset in [-3, -2, -1, 1, 2, 3]:
        target_d = ex_d + timedelta(days=offset)
        match = missing_days[(missing_days["station"] == stn) & (missing_days["date"] == target_d)]
        if len(match) > 0:
            pairs.append({
                "zone": z,
                "station": stn,
                "exceedance_date": str(ex_d),
                "exceedance_type": "DANGER" if ex_row["label_danger"] == 1 else "WARNING",
                "water_level_m": ex_row["daily_max"],
                "missing_date": str(target_d),
                "offset_days": offset
            })

pairs_df = pd.DataFrame(pairs)
pairs_df.to_csv(out_dir / "dropped_near_exceedance_pairs.csv", index=False)

# 4. Separate Exceedance Dates & Missing Dates
ex_dates_unique = pairs_df[["zone", "station", "exceedance_date", "exceedance_type", "water_level_m"]].drop_duplicates().reset_index(drop=True)
miss_dates_unique = pairs_df[["zone", "station", "missing_date"]].drop_duplicates().reset_index(drop=True)

ex_dates_unique.to_csv(out_dir / "exceedance_dates_with_near_drops.csv", index=False)
miss_dates_unique.to_csv(out_dir / "missing_dates_near_exceedances.csv", index=False)

report_lines = [
    "# Dropped / Missing Dates Near Exceedance Events Audit\n",
    f"Total distinct exceedance dates with a drop within ±3 days: {len(ex_dates_unique)}",
    f"Total distinct missing dates within ±3 days of an exceedance: {len(miss_dates_unique)}",
    f"Total near-drop paired relationships: {len(pairs_df)}\n",
    "## 1. Distinct Exceedance Dates Affected",
    "```",
    ex_dates_unique.to_string(index=False),
    "```\n",
    "## 2. Distinct Missing Dates within ±3 Days",
    "```",
    miss_dates_unique.to_string(index=False),
    "```\n",
    "## 3. Full Offset-by-Offset Relationship Table",
    "```",
    pairs_df.to_string(index=False),
    "```\n"
]

(out_dir / "dropped_near_exceedance_detailed.md").write_text("\n".join(report_lines), encoding="utf-8")
print("Report generated successfully.")
print("\nDistinct Exceedance Dates Affected:")
print(ex_dates_unique.to_string(index=False))
print("\nDistinct Missing Dates:")
print(miss_dates_unique.to_string(index=False))
