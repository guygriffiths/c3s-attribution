#!/usr/bin/env python3

import cdsapi

c = cdsapi.Client()

years = [str(y) for y in range(2010, 2021)]
years.reverse()
years.append(1990)

for year in years:
    print(f"Downloading {year}...")
    dataset = "derived-era5-single-levels-daily-statistics"
    request = {
        "product_type": "reanalysis",
        "variable": [
            "2m_temperature"
        ],
        "year": f"{year}",
        "month": [
            "01", "02", "03",
            "04", "05", "06",
            "07", "08", "09",
            "10", "11", "12"
        ],
        "day": [
            "01", "02", "03",
            "04", "05", "06",
            "07", "08", "09",
            "10", "11", "12",
            "13", "14", "15",
            "16", "17", "18",
            "19", "20", "21",
            "22", "23", "24",
            "25", "26", "27",
            "28", "29", "30",
            "31"
        ],
        "daily_statistic": "daily_max",
        "time_zone": "utc+00:00",
        "frequency": "1_hourly"
    }
    target = f"/data/max/era5_daily_max_temperature_{year}.nc"
    c.retrieve(
        dataset, request, target
    )
