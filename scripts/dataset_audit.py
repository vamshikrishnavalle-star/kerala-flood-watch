import pathlib
import pandas as pd
import numpy as np

out_dir = pathlib.Path("docs/step0")
out_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet("data/processed/dataset.parquet")
df["date"] = pd.to_datetime(df["date"])
df["year"] = df["date"].dt.year

# 1. Per-Zone Year Breakdown
records = []
for (z, yr), g in df.groupby(["zone", "year"]):
    n_rows = len(g)
    warn_pos = int(g["label_warning"].sum())
    dang_pos = int(g["label_danger"].sum())
    min_d = g["date"].min()
    max_d = g["date"].max()
    expected_days = (max_d - min_d).days + 1
    missing = expected_days - n_rows
    records.append({
        "zone": z, "year": yr, "rows": n_rows,
        "warning_pos": warn_pos, "danger_pos": dang_pos,
        "min_date": str(min_d.date()), "max_date": str(max_d.date()),
        "missing_days": missing
    })

res_df = pd.DataFrame(records)
res_df.to_csv(out_dir / "dataset_per_zone_year.csv", index=False)

# Pivot summary
piv_rows = res_df.pivot(index="year", columns="zone", values="rows")
piv_warn = res_df.pivot(index="year", columns="zone", values="warning_pos")
piv_dang = res_df.pivot(index="year", columns="zone", values="danger_pos")
piv_miss = res_df.pivot(index="year", columns="zone", values="missing_days")

summary_table = pd.concat([
    piv_rows.rename(columns=lambda c: f"{c}_rows"),
    piv_warn.rename(columns=lambda c: f"{c}_warn_pos"),
    piv_dang.rename(columns=lambda c: f"{c}_dang_pos"),
    piv_miss.rename(columns=lambda c: f"{c}_missing_days")
], axis=1)

summary_table.to_csv(out_dir / "dataset_summary_table.csv")

# Train vs Test Totals
train_df = df[df["year"] <= 2018]
test_df = df[df["year"] >= 2019]

reconciliation_rows = []
for z in sorted(df["zone"].unique()):
    tr = train_df[train_df["zone"] == z]
    te = test_df[test_df["zone"] == z]
    reconciliation_rows.append({
        "zone": z,
        "train_rows": len(tr),
        "train_warn_pos": int(tr["label_warning"].sum()),
        "train_dang_pos": int(tr["label_danger"].sum()),
        "test_rows": len(te),
        "test_warn_pos": int(te["label_warning"].sum()),
        "test_dang_pos": int(te["label_danger"].sum()),
    })

reconciliation_rows.append({
    "zone": "POOLED_TOTAL",
    "train_rows": len(train_df),
    "train_warn_pos": int(train_df["label_warning"].sum()),
    "train_dang_pos": int(train_df["label_danger"].sum()),
    "test_rows": len(test_df),
    "test_warn_pos": int(test_df["label_warning"].sum()),
    "test_dang_pos": int(test_df["label_danger"].sum()),
})

pd.DataFrame(reconciliation_rows).to_csv(out_dir / "positives_reconciliation.csv", index=False)

# Check 2018
y18 = df[df["year"] == 2018]
y18_summary = {
    "year": 2018,
    "pathanamthitta_warn": int(y18[y18["zone"] == "Pathanamthitta"]["label_warning"].sum()),
    "pathanamthitta_dang": int(y18[y18["zone"] == "Pathanamthitta"]["label_danger"].sum()),
    "kottayam_warn": int(y18[y18["zone"] == "Kottayam"]["label_warning"].sum()),
    "kottayam_dang": int(y18[y18["zone"] == "Kottayam"]["label_danger"].sum()),
    "pooled_warn": int(y18["label_warning"].sum()),
    "pooled_dang": int(y18["label_danger"].sum())
}

with open(out_dir / "year_2018_reconciliation.txt", "w") as f:
    f.write(f"""2018 Positives Reconciliation:
Pathanamthitta: Warning = {y18_summary['pathanamthitta_warn']}, Danger = {y18_summary['pathanamthitta_dang']}
Kottayam:       Warning = {y18_summary['kottayam_warn']}, Danger = {y18_summary['kottayam_dang']}
Pooled Total:   Warning = {y18_summary['pooled_warn']}, Danger = {y18_summary['pooled_dang']}
""")

print("Dataset audit complete. Files written to docs/step0/.")
