import glob, pandas as pd
for f in sorted(glob.glob("data/raw/labels/cwc/station_*.csv")):
    d = pd.read_csv(f, parse_dates=["dataTime"])
    d["year"] = d.dataTime.dt.year
    g = d.groupby("year").agg(rows=("dataValue", "size"),
                              days=("dataTime", lambda s: s.dt.date.nunique()))
    print(f, "-", len(d), "rows total")
    print(g.T.to_string()); print()
