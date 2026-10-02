# Dropped / Missing Dates Near Exceedance Events Audit

Total distinct exceedance dates with a drop within ±3 days: 3
Total distinct missing dates within ±3 days of an exceedance: 1
Total near-drop paired relationships: 3

## 1. Distinct Exceedance Dates Affected
```
          zone     station exceedance_date exceedance_type  water_level_m
Pathanamthitta KALLOOPPARA      2021-07-16          DANGER           6.10
Pathanamthitta KALLOOPPARA      2021-07-17          DANGER           6.08
Pathanamthitta KALLOOPPARA      2021-07-18         WARNING           5.01
```

## 2. Distinct Missing Dates within ±3 Days
```
          zone     station missing_date
Pathanamthitta KALLOOPPARA   2021-07-19
```

## 3. Full Offset-by-Offset Relationship Table
```
          zone     station exceedance_date exceedance_type  water_level_m missing_date  offset_days
Pathanamthitta KALLOOPPARA      2021-07-16          DANGER           6.10   2021-07-19            3
Pathanamthitta KALLOOPPARA      2021-07-17          DANGER           6.08   2021-07-19            2
Pathanamthitta KALLOOPPARA      2021-07-18         WARNING           5.01   2021-07-19            1
```
