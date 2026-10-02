import httpx, json, time, os, pandas as pd
from pathlib import Path

out_dir = Path("data/raw/labels/cwc")
out_dir.mkdir(parents=True, exist_ok=True)

url = "https://indiawris.gov.in/Dataset/River Water Level"

districts = [
    "Ernakulam",
    "Pathanamthitta",
    "Thrissur",
    "Alappuzha",
    "Kottayam",
    "Idukki",
    "Wayanad",
    "Palakkad",
    "Malappuram"
]

all_stations = []
all_readings = []

# Fetch for critical monsoon/flood periods (2018, 2019, 2020, 2021, 2022, 2023, 2024)
years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]

headers = {
    "accept": "application/json",
    "User-Agent": "Mozilla/5.0"
}

with httpx.Client(timeout=30.0, verify=False) as client:
    for dist in districts:
        print(f"\n==========================================")
        print(f"Fetching CWC Water Level for District: {dist}")
        print(f"==========================================")
        dist_records = []
        
        for yr in years:
            # Focus on full monsoon window (June 1 to October 31)
            params = {
                "stateName": "Kerala",
                "districtName": dist,
                "agencyName": "CWC",
                "startdate": f"{yr}-06-01",
                "enddate": f"{yr}-10-31",
                "download": "false",
                "page": 0,
                "size": 1000
            }
            try:
                r = client.post(url, params=params, headers=headers)
                if r.status_code == 200:
                    resp_json = r.json()
                    data = resp_json.get("data", [])
                    if data:
                        print(f"  Year {yr}: {len(data)} water level readings fetched")
                        dist_records.extend(data)
                    else:
                        print(f"  Year {yr}: No CWC records returned")
                else:
                    print(f"  Year {yr}: HTTP {r.status_code}")
            except Exception as e:
                print(f"  Year {yr}: Request error {e}")
            
            time.sleep(0.5)
        
        if dist_records:
            df_dist = pd.DataFrame(dist_records)
            out_file = out_dir / f"cwc_{dist.lower()}_water_levels.csv"
            df_dist.to_csv(out_file, index=False)
            print(f"==> Saved {len(df_dist)} records to {out_file}")
            
            # Collect unique stations
            station_info = df_dist[['stationCode', 'stationName', 'district', 'tributary', 'latitude', 'longitude']].drop_duplicates()
            all_stations.append(station_info)
            all_readings.append(df_dist)

if all_stations:
    stations_summary = pd.concat(all_stations).drop_duplicates()
    stations_summary.to_csv("data/raw/labels/cwc_kerala_stations_catalog.csv", index=False)
    print("\n==========================================")
    print(f"Total Unique CWC Kerala Stations Found: {len(stations_summary)}")
    print("==========================================")
    print(stations_summary.to_string(index=False))

print("\nData fetch complete!")
