"""Test persistent requests.Session speed
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import time

s = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10))

API_URL = "https://indiawris.gov.in/Dataset/River Water Level"
HEADERS = {"accept": "application/json", "User-Agent": "Mozilla/5.0"}

t0 = time.time()
for m in range(1, 13):
    params = {
        "stateName": "Kerala", "districtName": "Idukki", "stationCode": "016-SWRDKOCHI",
        "agencyName": "CWC", "startdate": f"2000-{m:02d}-01", "enddate": f"2000-{m:02d}-28",
        "download": "false", "page": 0, "size": 1000
    }
    r = s.post(API_URL, params=params, headers=HEADERS, timeout=15)
    print(f"Month {m}: status {r.status_code}, rows {len(r.json().get('data', []))}, elapsed: {time.time()-t0:.2f}s")
