"""Test thread-local client concurrency
"""
from concurrent.futures import ThreadPoolExecutor
import threading
import httpx
import time

thread_local = threading.local()

def get_client():
    if not hasattr(thread_local, "client"):
        thread_local.client = httpx.Client(timeout=15.0, verify=True)
    return thread_local.client

API_URL = "https://indiawris.gov.in/Dataset/River Water Level"
HEADERS = {"accept": "application/json", "User-Agent": "Mozilla/5.0"}

def fetch_one(m):
    c = get_client()
    p = {
        "stateName": "Kerala", "districtName": "Idukki", "stationCode": "016-SWRDKOCHI",
        "agencyName": "CWC", "startdate": f"2000-{m:02d}-01", "enddate": f"2000-{m:02d}-28",
        "download": "false", "page": 0, "size": 1000
    }
    r = c.post(API_URL, params=p, headers=HEADERS)
    return m, len(r.json().get("data", []))

t0 = time.time()
with ThreadPoolExecutor(max_workers=3) as ex:
    res = list(ex.map(fetch_one, range(1, 13)))
print("Fetched 12 months in:", f"{time.time()-t0:.2f}s", "Results:", res)
