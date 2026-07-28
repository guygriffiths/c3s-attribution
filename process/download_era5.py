#!/usr/bin/env python3
"""
ERA5 Daily Temperature Statistics Downloader

Downloads daily temperature statistics (min, max, mean), total precipitation,
and land-sea mask from the Copernicus Climate Data Store (CDS) ERA5 reanalysis
dataset. Automatically detects missing years and downloads only what's needed.

Output directory structure:
    <output_dir>/t2m/min/   - Daily minimum 2m temperature
    <output_dir>/t2m/max/   - Daily maximum 2m temperature
    <output_dir>/t2m/mean/  - Daily mean 2m temperature
    <output_dir>/precip/    - Daily total precipitation

Usage:
    # Download all missing data for all variables
    python download_era5.py

    # Or import and use programmatically
    from download_era5 import download_all_latest, download_year, download_precip_year
    download_all_latest()
    download_year(2024, 'max', output_dir='/custom/path')
    download_precip_year(2024, output_dir='/custom/path')
"""

import logging, sys
from pathlib import Path
from datetime import datetime
from typing import List, Set, Optional

import cdsapi


# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only add handler if we don't have one already
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)

# Constants
TEMP_DATASET = "derived-era5-single-levels-daily-statistics"
LAND_DATASET = "reanalysis-era5-land"
PRECIP_DATASET = "derived-era5-single-levels-daily-statistics"
STATISTICS = ["min", "max", "mean"]
START_YEAR = 1979
ALL_MONTHS = [f"{m:02d}" for m in range(1, 13)]
ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]


def get_existing_years(base_dir: Path, prefix: str) -> Set[int]:
    """
    Find which years are already downloaded for a given variable/stat.

    Args:
        base_dir: Directory containing downloaded NetCDF files
        prefix: File prefix to match (e.g. 'era5_daily_min_temperature' or
                'era5_daily_total_precipitation')

    Returns:
        Set of years (as integers) that exist on disk
    """
    pattern = f"{prefix}_*.nc"
    existing_years = {
        int(p.stem.split("_")[-1])
        for p in base_dir.glob(pattern)
    }
    logger.debug(f"Found {len(existing_years)} existing years in {base_dir}")
    return existing_years


def get_missing_years(
    base_dir: Path,
    prefix: str,
    end_year: Optional[int] = None
) -> List[int]:
    """
    Determine which years are missing for a given variable/stat directory.

    Args:
        base_dir: Directory containing downloaded NetCDF files
        prefix: File prefix to match (see get_existing_years)
        end_year: Latest year to consider (default: current year)

    Returns:
        Sorted list of missing years
    """
    if end_year is None:
        end_year = datetime.now().year

    existing_years = get_existing_years(base_dir, prefix)
    expected_years = set(range(START_YEAR, end_year + 1))
    missing_years = sorted(expected_years - existing_years)

    logger.info(
        f"{base_dir.name}: {len(missing_years)} missing years "
        f"out of {len(expected_years)} total"
    )
    return missing_years


def download_land_sea_mask(
    output_dir: str = "/data",
    client: Optional[cdsapi.Client] = None
) -> bool:
    """
    Download ERA5 land-sea mask if not already present.

    The land-sea mask is a static field used to classify events as land-only,
    ocean-only, or mixed. Only needs to be downloaded once.

    Args:
        output_dir: Base directory for output file (default: '/data')
        client: Optional CDS API client (creates new one if not provided)

    Returns:
        True if mask exists or download succeeded, False otherwise
    """
    output_path = Path(output_dir) / "era5_land_sea_mask.nc"

    if output_path.exists():
        logger.info(f"Land-sea mask already exists at {output_path}")
        return True

    if client is None:
        client = cdsapi.Client()

    logger.info(f"Downloading land-sea mask to {output_path}")

    try:
        request = {
            "variable": ["land_sea_mask"],
            "data_format": "netcdf",
            "download_format": "unarchived"
        }
        client.retrieve(LAND_DATASET, request, str(output_path))
        logger.info("Successfully downloaded land-sea mask")
        return True

    except Exception as e:
        logger.error(f"Failed to download land-sea mask: {e}")
        return False


def download_year(
    year: int,
    stat: str,
    output_dir: str = "/data",
    client: Optional[cdsapi.Client] = None
) -> bool:
    """
    Download a single year of daily 2m temperature statistics from ERA5.

    Files are written to <output_dir>/t2m/<stat>/era5_daily_<stat>_temperature_<year>.nc

    Args:
        year: Year to download (1979 to present)
        stat: Temperature statistic ('min', 'max', or 'mean')
        output_dir: Base directory for output files (default: '/data')
        client: Optional CDS API client (creates new one if not provided)

    Returns:
        True if download succeeded, False otherwise

    Raises:
        ValueError: If stat is not one of 'min', 'max', 'mean'
    """
    if stat not in STATISTICS:
        raise ValueError(f"stat must be one of {STATISTICS}, got '{stat}'")

    if year < START_YEAR or year > datetime.now().year:
        raise ValueError(
            f"year must be between {START_YEAR} and {datetime.now().year}, "
            f"got {year}"
        )

    if client is None:
        client = cdsapi.Client()

    base_dir = Path(output_dir) / "t2m" / stat
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"era5_daily_{stat}_temperature_{year}.nc"

    request = {
        "product_type": "reanalysis",
        "variable": ["2m_temperature"],
        "year": f"{year}",
        "month": ALL_MONTHS,
        "day": ALL_DAYS,
        "daily_statistic": f"daily_{stat}",
        "time_zone": "utc+00:00",
        "frequency": "1_hourly"
    }

    logger.info(f"Downloading {year} t2m/{stat} to {target}")

    try:
        client.retrieve(TEMP_DATASET, request, str(target))
        logger.info(f"Successfully downloaded {year} t2m/{stat}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {year} t2m/{stat}: {e}")
        return False


def download_precip_year(
    year: int,
    output_dir: str = "/data",
    client: Optional[cdsapi.Client] = None
) -> bool:
    """
    Download a single year of daily total precipitation from ERA5.

    Files are written to <output_dir>/precip/era5_daily_total_precipitation_<year>.nc

    Args:
        year: Year to download (1979 to present)
        output_dir: Base directory for output files (default: '/data')
        client: Optional CDS API client (creates new one if not provided)

    Returns:
        True if download succeeded, False otherwise
    """
    if year < START_YEAR or year > datetime.now().year:
        raise ValueError(
            f"year must be between {START_YEAR} and {datetime.now().year}, "
            f"got {year}"
        )

    if client is None:
        client = cdsapi.Client()

    base_dir = Path(output_dir) / "precip"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"era5_daily_total_precipitation_{year}.nc"

    request = {
        "product_type": "reanalysis",
        "variable": ["total_precipitation"],
        "year": f"{year}",
        "month": ALL_MONTHS,
        "day": ALL_DAYS,
        "daily_statistic": "daily_mean",  # ERA5 daily sum is accessed via daily_mean for accumulations
        "time_zone": "utc+00:00",
        "frequency": "1_hourly"
    }

    logger.info(f"Downloading {year} precip to {target}")

    try:
        client.retrieve(PRECIP_DATASET, request, str(target))
        logger.info(f"Successfully downloaded {year} precip")
        return True
    except Exception as e:
        logger.error(f"Failed to download {year} precip: {e}")
        return False


def _apply_partial_year_logic(missing_years: List[int]) -> List[int]:
    """
    Ensure the current year and, in January, the previous year are always
    included so partial/updated data is re-fetched.
    """
    current_year = datetime.now().year
    missing_set = set(missing_years)

    if datetime.now().month == 1:
        missing_set.add(current_year - 1)
    missing_set.add(current_year)

    return sorted(missing_set)


def download_all_latest(
    output_dir: str = "/data",
    statistics: Optional[List[str]] = None,
    include_precip: bool = True,
    include_land_sea_mask: bool = True
) -> dict:
    """
    Download all missing years for all temperature statistics and precipitation.

    Scans the output directory for existing files and downloads only
    missing years from 1979 to the current year.

    Directory layout produced:
        <output_dir>/t2m/min/
        <output_dir>/t2m/max/
        <output_dir>/t2m/mean/
        <output_dir>/precip/

    Args:
        output_dir: Base directory for output files (default: '/data')
        statistics: List of t2m statistics to download (default: all)
        include_precip: Download total precipitation (default: True)
        include_land_sea_mask: Download land-sea mask if missing (default: True)

    Returns:
        Dictionary with download results:
        {
            'land_sea_mask': True,
            't2m_min': {'success': [2023, 2024], 'failed': []},
            't2m_max': {'success': [2023], 'failed': [2024]},
            't2m_mean': {'success': [...], 'failed': [...]},
            'precip': {'success': [...], 'failed': [...]},
        }
    """
    if statistics is None:
        statistics = STATISTICS

    invalid = set(statistics) - set(STATISTICS)
    if invalid:
        raise ValueError(f"Invalid statistics: {invalid}")

    logger.info("=" * 60)
    logger.info("ERA5 Data Downloader")
    logger.info("=" * 60)
    logger.info(f"T2M statistics: {statistics}")
    logger.info(f"Precipitation: {include_precip}")
    logger.info(f"Output directory: {output_dir}")

    client = cdsapi.Client()
    results = {}

    # ------------------------------------------------------------------ #
    # Land-sea mask
    # ------------------------------------------------------------------ #
    if include_land_sea_mask:
        logger.info("\n--- Checking land-sea mask ---")
        mask_success = download_land_sea_mask(output_dir, client)
        results['land_sea_mask'] = mask_success
        if not mask_success:
            logger.warning("Land-sea mask download failed, continuing anyway")

    # ------------------------------------------------------------------ #
    # 2m temperature statistics  →  t2m/<stat>/
    # ------------------------------------------------------------------ #
    for stat in statistics:
        key = f"t2m_{stat}"
        results[key] = {'success': [], 'failed': []}

    for stat in statistics:
        key = f"t2m_{stat}"
        logger.info(f"\n--- Processing t2m/{stat} ---")
        base_dir = Path(output_dir) / "t2m" / stat
        base_dir.mkdir(parents=True, exist_ok=True)

        missing_years = get_missing_years(
            base_dir, f"era5_daily_{stat}_temperature"
        )
        missing_years = _apply_partial_year_logic(missing_years)

        logger.info(f"t2m/{stat}: Downloading {len(missing_years)} years")

        for year in missing_years:
            success = download_year(year, stat, output_dir, client)
            if success:
                results[key]['success'].append(year)
            else:
                results[key]['failed'].append(year)

    # ------------------------------------------------------------------ #
    # Total precipitation  →  precip/
    # ------------------------------------------------------------------ #
    if include_precip:
        results['precip'] = {'success': [], 'failed': []}
        logger.info("\n--- Processing precip ---")
        precip_dir = Path(output_dir) / "precip"
        precip_dir.mkdir(parents=True, exist_ok=True)

        missing_years = get_missing_years(
            precip_dir, "era5_daily_total_precipitation"
        )
        missing_years = _apply_partial_year_logic(missing_years)

        logger.info(f"precip: Downloading {len(missing_years)} years")

        for year in missing_years:
            success = download_precip_year(year, output_dir, client)
            if success:
                results['precip']['success'].append(year)
            else:
                results['precip']['failed'].append(year)

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    logger.info("\n" + "=" * 60)
    logger.info("Download Summary")
    logger.info("=" * 60)

    if include_land_sea_mask:
        mask_status = "✓ Present" if results.get('land_sea_mask') else "✗ Failed"
        logger.info(f"Land-sea mask: {mask_status}")

    for key, value in results.items():
        if key == 'land_sea_mask':
            continue
        total = len(value['success']) + len(value['failed'])
        if total == 0:
            logger.info(f"{key}: All years already existed")
        else:
            logger.info(f"{key}: {len(value['success'])}/{total} successful")
            if value['failed']:
                logger.warning(f"  Failed years: {value['failed']}")

    return results


def main():
    """Main entry point when run as a script."""
    try:
        results = download_all_latest()

        total_failed = 0
        for key, value in results.items():
            if key == 'land_sea_mask':
                if not value:
                    total_failed += 1
            else:
                total_failed += len(value.get('failed', []))

        if total_failed > 0:
            logger.error(f"Completed with {total_failed} failed downloads")
            return 1

        logger.info("All downloads completed successfully!")
        return 0

    except KeyboardInterrupt:
        logger.warning("Download interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())