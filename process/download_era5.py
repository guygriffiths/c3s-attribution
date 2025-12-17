#!/usr/bin/env python3

import cdsapi
from pathlib import Path
from datetime import datetime


c = cdsapi.Client()

# To download the entire ERA5 dataset, uncomment the following lines:
# years = [str(y) for y in range(1979, 2026)]
# years.reverse()


for stat in ["min", "max", "mean"]:
    base = Path(f"/data/{stat}")  
    # years present on disk
    existing_years = {
        int(p.stem.split("_")[-1])
        for p in base.glob(f"era5_daily_{stat}_temperature_*.nc")
    }

    # years that should exist
    current_year = datetime.now().year
    expected_years = set(range(1979, current_year + 1))

    # missing years
    missing_years = sorted(expected_years - existing_years)
    for year in missing_years:
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
            "daily_statistic": f"daily_{stat}",
            "time_zone": "utc+00:00",
            "frequency": "1_hourly"
        }
        target = f"/data/{stat}/era5_daily_{stat}_temperature_{year}.nc"
        c.retrieve(
            dataset, request, target
        )
