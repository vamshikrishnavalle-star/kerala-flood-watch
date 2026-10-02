import json, os, calendar, httpx, pandas as pd

API_URL = "https://indiawris.gov.in/Dataset/River Water Level"
HEADERS = {"accept": "application/json", "User-Agent": "Mozilla/5.0"}

print("=== 1. TEST API CAPABILITIES (stationCode, sort, orderBy) ===")
with httpx.Client(timeout=30.0) as client:
    # Test 1: stationCode filter
    p1 = {
        "stateName": "Kerala", "districtName": "Idukki", "agencyName": "CWC",
        "stationCode": "016-SWRDKOCHI",
        "startdate": "2018-08-01", "enddate": "2018-08-02", "page": 0, "size": 10
    }
    r1 = client.post(API_URL, params=p1, headers=HEADERS)
    d1 = r1.json().get("data", []) if r1.status_code == 200 else []
    st_codes1 = set(d.get("stationCode") for d in d1)
    print(f"Test with stationCode='016-SWRDKOCHI': {len(d1)} rows returned, unique stationCodes in result: {st_codes1}")
    
    # Test 2: orderBy / sort
    p2 = {
        "stateName": "Kerala", "districtName": "Idukki", "agencyName": "CWC",
        "startdate": "2018-08-01", "enddate": "2018-08-02", "page": 0, "size": 10,
        "orderBy": "dataTime", "sort": "asc"
    }
    r2 = client.post(API_URL, params=p2, headers=HEADERS)
    d2 = r2.json().get("data", []) if r2.status_code == 200 else []
    ts2 = [d.get("dataTime") for d in d2]
    print(f"Test with orderBy/sort: {len(d2)} rows returned, timestamps: {ts2[:5]}")

print("\n=== 2. CLASSIFY 1,097 ZERO-ROW RESPONSES FROM V2 LOG ===")
with open("data/raw/labels/cwc/v2/v2_requests_log.json") as f:
    v2_logs = json.load(f)

log_df = pd.DataFrame(v2_logs)
zero_rows = log_df[log_df["matched_rows"] == 0]
print(f"Total entries in log: {len(log_df)}")
print(f"Entries with matched_rows == 0: {len(zero_rows)}")
print(f"Breakdown of total_page_rows for matched_rows == 0:")
print(zero_rows["total_page_rows"].value_counts(dropna=False).to_string())

# Terminating empty page vs empty month
page_gt_0 = zero_rows[zero_rows["page"] > 0]
page_0 = zero_rows[zero_rows["page"] == 0]
print(f"\nZero-row entries with page > 0 (terminating pagination pages): {len(page_gt_0)}")
print(f"Zero-row entries with page == 0 (entire month returned 0 rows or no match): {len(page_0)}")
print(f"  Of page == 0, total_page_rows == 0 (API returned empty []): {(page_0['total_page_rows'] == 0).sum()}")
print(f"  Of page == 0, total_page_rows > 0 (district had data, but this station had 0): {(page_0['total_page_rows'] > 0).sum()}")

print("\n=== 3. LOG ENTRIES FOR KALLOOPPARA 2018 & ARANGALI AUG 17-19 2018 ===")
kall_2018 = [l for l in v2_logs if l.get("stationCode") == "017-SWRDKOCHI" and "2018" in str(l.get("startdate", ""))]
print(f"Kallooppara 2018 log entries count: {len(kall_2018)}")
for l in kall_2018:
    print(l)

# Check exception entries for Kallooppara
kall_exceptions = [l for l in v2_logs if l.get("stationCode") == "017-SWRDKOCHI" and "exception" in l]
print(f"Kallooppara total logged exceptions: {len(kall_exceptions)}")
for e in kall_exceptions[:5]:
    print("  ", e)

# Check Arangali Aug 2018 in v2 logs
arang_aug18 = [l for l in v2_logs if l.get("stationCode") == "011-SWRDKOCHI" and l.get("startdate") == "2018-08-01"]
print(f"\nArangali Aug 2018 log entries: {len(arang_aug18)}")
for l in arang_aug18:
    print(l)
