import pathlib
from datetime import timedelta
import pandas as pd

out_dir = pathlib.Path("docs/step0")
out_dir.mkdir(parents=True, exist_ok=True)

PROCESSED_DIR = pathlib.Path("data/processed")
ds_df = pd.read_parquet(PROCESSED_DIR / "dataset.parquet")
ds_df["date"] = pd.to_datetime(ds_df["date"])

exceed_dates = ds_df[(ds_df["label_danger"] == 1) | (ds_df["label_warning"] == 1)]["date"].dt.date.unique()

labels_raw_path = PROCESSED_DIR / "labels_daily.csv"
if labels_raw_path.exists():
    labels_raw = pd.read_csv(labels_raw_path)
    labels_raw["date"] = pd.to_datetime(labels_raw["date"]).dt.date
    dropped_days = labels_raw[labels_raw["label_warning"].isna()]["date"].unique()
else:
    # Check date gaps in ds_df for each zone
    all_dates = pd.date_range("2000-01-01", "2024-12-31").date
    kp_dates = ds_df[ds_df["zone"] == "Pathanamthitta"]["date"].dt.date.unique()
    dropped_days = [d for d in all_dates if d not in kp_dates]

near_drops = []
for ed in exceed_dates:
    for offset in [-3, -2, -1, 1, 2, 3]:
        check_d = ed + timedelta(days=offset)
        if check_d in dropped_days:
            near_drops.append((ed, check_d, offset))

with open(out_dir / "dropped_days_near_exceedance.txt", "w") as f:
    f.write(f"Dropped / Missing Days within ±3 Days of an Exceedance Event:\n")
    f.write(f"Total occurrences: {len(near_drops)}\n\n")
    if near_drops:
        for ed, cd, off in near_drops:
            f.write(f"  Exceedance Date: {ed} | Dropped NaN Day: {cd} (Offset: {off:+d} days)\n")
    else:
        f.write("  None: 0 dropped days within ±3 days of any warning or danger exceedance.\n")

print(f"Dropped days check complete. Total near drops: {len(near_drops)}")
