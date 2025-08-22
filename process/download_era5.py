#!/usr/bin/env python3

import cdsapi

c = cdsapi.Client()

years = [str(y) for y in range(1979, 1990)] + [str(y) for y in range(2021, 2025)]
years.reverse()

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
        "daily_statistic": "daily_min",
        "time_zone": "utc+00:00",
        "frequency": "1_hourly"
    }
    target = f"/data/min/era5_daily_min_temperature_{year}.nc"
    c.retrieve(
        dataset, request, target
    )
