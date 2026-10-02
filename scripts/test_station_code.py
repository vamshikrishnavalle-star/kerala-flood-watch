import httpx

API_URL = "https://indiawris.gov.in/Dataset/River Water Level"
HEADERS = {"accept": "application/json", "User-Agent": "Mozilla/5.0"}

with httpx.Client(timeout=30.0) as client:
    # Test stationCode directly
    params = {
        "stateName": "Kerala",
        "stationCode": "017-SWRDKOCHI",
        "agencyName": "CWC",
        "startdate": "2018-08-01",
        "enddate": "2018-08-31",
        "page": 0,
        "size": 1000
    }
    r = client.post(API_URL, params=params, headers=HEADERS)
    print("Status:", r.status_code)
    if r.status_code == 200:
        data = r.json().get("data", [])
        print("Rows returned for 017-SWRDKOCHI in Aug 2018:", len(data))
        if data:
            print("First row:", data[0])
            print("Last row:", data[-1])
            # Check unique stations
            codes = set(d.get("stationCode") for d in data)
            print("Unique station codes:", codes)
