import pathlib, sys
from datetime import date
import pandas as pd
import numpy as np

def count_clusters(vals):
    n, in_c = 0, False
    for v in vals:
        if v == 1:
            if not in_c: n += 1; in_c = True
        else: in_c = False
    return n

df = pd.read_parquet("data/processed/dataset.parquet")
df["year"] = pd.to_datetime(df["date"]).dt.year

tot_d = int((df["label_danger"] == 1).sum())
tot_w = int((df["label_warning"] == 1).sum())
tot_rows = len(df)

# Check thresholds & 2018
warns = []
if tot_d < 100:
    warns.append(f"WARNING: Total danger positives ({tot_d}) < 100 threshold")
if tot_w < 100:
    warns.append(f"WARNING: Total warning positives ({tot_w}) < 100 threshold")

for z in df["zone"].unique():
    zd = int((df[df["zone"] == z]["label_danger"] == 1).sum())
    if zd < 10:
        warns.append(f"WARNING: Zone {z} danger positives ({zd}) < 10 threshold")

d_2018 = int((df[df["year"] == 2018]["label_danger"] == 1).sum())
if d_2018 == 0:
    warns.append("WARNING: 2018 has 0 danger positives (critical flood year!)")

# Positives by zone, year, regime, event
summary_rows = []
for z, zgrp in df.groupby("zone"):
    for yr, ygrp in zgrp.groupby("year"):
        ygrp_sorted = ygrp.sort_values("date")
        nd = int((ygrp_sorted["label_danger"] == 1).sum())
        nw = int((ygrp_sorted["label_warning"] == 1).sum())
        cd = count_clusters(ygrp_sorted["label_danger"].tolist())
        cw = count_clusters(ygrp_sorted["label_warning"].tolist())
        regimes = ",".join(sorted(ygrp["regime"].unique()))
        summary_rows.append({
            "zone": z, "year": yr, "days": len(ygrp),
            "danger_pos": nd, "warning_pos": nw,
            "danger_events": cd, "warning_events": cw,
            "regimes": regimes
        })

sum_df = pd.DataFrame(summary_rows)

md = f"""# Phase 2 Dataset Audit Report

Generated: {date.today().isoformat()}

## 1. Executive Summary

- **Total Rows**: {tot_rows:,}
- **Zones Included**: {", ".join(sorted(df["zone"].unique()))}
- **Date Range**: {df["date"].min().date()} to {df["date"].max().date()}
- **Total Danger Positives**: {tot_d} ({tot_d/tot_rows:.2%})
- **Total Warning Positives**: {tot_w} ({tot_w/tot_rows:.2%})

### Threshold Validation Checks
"""

if not warns:
    md += "\n> [!NOTE]\n> **ALL AUDIT CHECKS PASSED**: Total positives >= 100, each zone >= 10, 2018 flood year verified non-zero.\n\n"
else:
    for w in warns:
        md += f"\n> [!WARNING]\n> {w}\n"

md += f"""
## 2. Positives by Zone, Year, Event, and Regime

| Zone | Year | Total Days | >= Danger | Danger Events | >= Warning | Warning Events | Regimes |
|:---|---:|---:|---:|---:|---:|---:|:---|
"""
for _, r in sum_df.iterrows():
    md += f"| {r['zone']} | {r['year']} | {r['days']} | {r['danger_pos']} | {r['danger_events']} | {r['warning_pos']} | {r['warning_events']} | {r['regimes']} |\n"

md += f"""
## 3. Totals by Zone

| Zone | Total Days | >= Danger | Danger Events | >= Warning | Warning Events |
|:---|---:|---:|---:|---:|---:|
"""
for z, zgrp in df.groupby("zone"):
    z_sorted = zgrp.sort_values("date")
    nd = int((z_sorted["label_danger"] == 1).sum())
    nw = int((z_sorted["label_warning"] == 1).sum())
    cd = count_clusters(z_sorted["label_danger"].tolist())
    cw = count_clusters(z_sorted["label_warning"].tolist())
    md += f"| {z} | {len(zgrp):,} | {nd} | {cd} | {nw} | {cw} |\n"

md += f"| **TOTAL** | **{tot_rows:,}** | **{tot_d}** | **{sum_df['danger_events'].sum()}** | **{tot_w}** | **{sum_df['warning_events'].sum()}** |\n"

pathlib.Path("docs/data-audit.md").write_text(md, encoding="utf-8")
print(md)
