import re, pathlib
p = pathlib.Path("docs/data-notes.md")
t = p.read_text(encoding="utf-8")

# 1. Unverified elevations -> coordinates that were verified against zones.py
t = re.sub(r"\| Elevation & Zone Coordinates \|.*?\|\n",
           "| Zone Coordinates | `src/ingest/zones.py` | Point coordinates | Kozhencherry (9.3364 N, 76.6974 E), Pala (9.7100 N, 76.6800 E) |\n",
           t, flags=re.S, count=1)

# 2. Absence of a located level is not proof that none exists
t = t.replace("but no official bulletin threshold.", "but no official threshold was located.")

# 3. Pre-2015 sampling: remove the unsupported times and the inaccurate claim
t = re.sub(r"1\. \*\*Pre-2015 Sampling Schedule\*\*:.*?exceedances\.",
           "1. **Pre-2015 Sampling Schedule**: Before 2015 the CWC series has 3 readings per day, "
           "so short peaks between readings can be missed. Pre-2015 days labeled 0 may therefore "
           "include unobserved exceedances (about 20 of the 47 Kalloopara danger events fall in this era). "
           "The monthly regime rule only controls which days are labeled NaN; it cannot recover unrecorded peaks. "
           "Results should be reported separately for the 3-per-day and hourly regimes.",
           t, flags=re.S, count=1)
p.write_text(t, encoding="utf-8")
