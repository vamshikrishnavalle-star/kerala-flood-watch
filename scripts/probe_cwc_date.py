import httpx, json

CWC_URL = "https://indiawris.gov.in/Dataset/River Water Level"

probe_periods = [
    ("2024 Full",    "2024-01-01", "2024-12-31"),
    ("2025 Full",    "2025-01-01", "2025-12-31"),
    ("2026 Q1",      "2026-01-01", "2026-03-31"),
    ("2026 Monsoon", "2026-06-01", "2026-10-02"),
]

with httpx.Client(timeout=30.0, verify=False) as client:
    for pname, s_dt, e_dt in probe_periods:
        params = {
            "stateName": "Kerala",
            "districtName": "Pathanamthitta",
            "agencyName": "CWC",
            "stationCode": "017-SWRDKOCHI",
            "startdate": s_dt,
            "enddate": e_dt,
            "page": 0,
            "size": 1000
        }
        r = client.post(CWC_URL, params=params)
        print(f"Probe {pname} ({s_dt} to {e_dt}): HTTP {r.status_code}")
        if r.status_code == 200:
            res_j = r.json()
            data = res_j if isinstance(res_j, list) else res_j.get("data", res_j.get("result", []))
            print(f"  Total records returned: {len(data)}")
            if len(data) > 0:
                print(f"  First: {data[0].get('dataTime')}, Last: {data[-1].get('dataTime')}")
        else:
            print(f"  Body: {r.text[:200]}")