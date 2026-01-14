#!/usr/bin/env python3
"""
ERA5 Daily Temperature Statistics Downloader

Downloads daily temperature statistics (min, max, mean) and land-sea mask from
the Copernicus Climate Data Store (CDS) ERA5 reanalysis dataset. Automatically
detects missing years and downloads only what's needed.

Usage:
    # Download all missing data for all statistics
    python download_era5.py

    # Or import and use programmatically
    from download_era5 import download_all_latest, download_year
    download_all_latest()
    download_year(2024, 'max', output_dir='/custom/path')
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
STATISTICS = ["min", "max", "mean"]
START_YEAR = 1979
ALL_MONTHS = [f"{m:02d}" for m in range(1, 13)]
ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]


def get_existing_years(base_dir: Path, stat: str) -> Set[int]:
    """
    Find which years are already downloaded for a given statistic.
    
    Args:
        base_dir: Directory containing downloaded NetCDF files
        stat: Temperature statistic ('min', 'max', or 'mean')
        
    Returns:
        Set of years (as integers) that exist on disk
    """
    pattern = f"era5_daily_{stat}_temperature_*.nc"
    existing_years = {
        int(p.stem.split("_")[-1])
        for p in base_dir.glob(pattern)
    }
    logger.debug(f"Found {len(existing_years)} existing years for {stat}")
    return existing_years


def get_missing_years(
    base_dir: Path,
    stat: str,
    end_year: Optional[int] = None
) -> List[int]:
    """
    Determine which years are missing for a given statistic.
    
    Args:
        base_dir: Directory containing downloaded NetCDF files
        stat: Temperature statistic ('min', 'max', or 'mean')
        end_year: Latest year to consider (default: current year)
        
    Returns:
        Sorted list of missing years
    """
    if end_year is None:
        end_year = datetime.now().year
    
    existing_years = get_existing_years(base_dir, stat)
    expected_years = set(range(START_YEAR, end_year + 1))
    missing_years = sorted(expected_years - existing_years)
    
    logger.info(
        f"{stat}: {len(missing_years)} missing years "
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
    # Check if already exists
    output_path = Path(output_dir) / "era5_land_sea_mask.nc"
    
    if output_path.exists():
        logger.info(f"Land-sea mask already exists at {output_path}")
        return True
    
    # Initialize client if not provided
    if client is None:
        client = cdsapi.Client()
    
    logger.info(f"Downloading land-sea mask to {output_path}")
    
    try:
        dataset = LAND_DATASET
        request = {
            "variable": ["land_sea_mask"],
            "data_format": "netcdf",
            "download_format": "unarchived"
        }
        
        client.retrieve(dataset, request, str(output_path))
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
    Download a single year of daily temperature statistics from ERA5.
    
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
    
    # Initialize client if not provided
    if client is None:
        client = cdsapi.Client()
    
    # Set up paths
    base_dir = Path(output_dir) / stat
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"era5_daily_{stat}_temperature_{year}.nc"
    
    # Build request
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
    
    logger.info(f"Downloading {year} {stat} to {target}")
    
    try:
        client.retrieve(TEMP_DATASET, request, str(target))
        logger.info(f"Successfully downloaded {year} {stat}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {year} {stat}: {e}")
        return False


def download_all_latest(
    output_dir: str = "/data",
    statistics: Optional[List[str]] = None,
    include_land_sea_mask: bool = True
) -> dict:
    """
    Download all missing years for all temperature statistics.
    
    Scans the output directory for existing files and downloads only
    missing years from 1979 to the current year. Optionally downloads
    the land-sea mask if not present.
    
    Args:
        output_dir: Base directory for output files (default: '/data')
        statistics: List of statistics to download (default: all)
        include_land_sea_mask: Download land-sea mask if missing (default: True)
        
    Returns:
        Dictionary with download results:
        {
            'land_sea_mask': True,
            'min': {'success': [2023, 2024], 'failed': []},
            'max': {'success': [2023], 'failed': [2024]},
            ...
        }
    """
    if statistics is None:
        statistics = STATISTICS
    
    # Validate statistics
    invalid = set(statistics) - set(STATISTICS)
    if invalid:
        raise ValueError(f"Invalid statistics: {invalid}")
    
    logger.info("=" * 60)
    logger.info("ERA5 Data Downloader")
    logger.info("=" * 60)
    logger.info(f"Statistics: {statistics}")
    logger.info(f"Output directory: {output_dir}")
    
    # Initialize CDS API client once
    client = cdsapi.Client()
    
    # Track results
    results = {}
    
    # Download land-sea mask first if requested
    if include_land_sea_mask:
        logger.info("\n--- Checking land-sea mask ---")
        mask_success = download_land_sea_mask(output_dir, client)
        results['land_sea_mask'] = mask_success
        if not mask_success:
            logger.warning("Land-sea mask download failed, continuing anyway")
    
    # Initialize results for temperature statistics
    for stat in statistics:
        results[stat] = {'success': [], 'failed': []}
    
    # Download missing data for each statistic
    for stat in statistics:
        logger.info(f"\n--- Processing {stat} ---")
        base_dir = Path(output_dir) / stat
        base_dir.mkdir(parents=True, exist_ok=True)
        
        missing_years = get_missing_years(base_dir, stat)
        
        if not missing_years:
            logger.info(f"{stat}: No missing years, all up to date!")
            continue
        
        logger.info(f"{stat}: Downloading {len(missing_years)} missing years")
        
        for year in missing_years:
            success = download_year(year, stat, output_dir, client)
            
            if success:
                results[stat]['success'].append(year)
            else:
                results[stat]['failed'].append(year)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Download Summary")
    logger.info("=" * 60)
    
    # Land-sea mask summary
    if include_land_sea_mask:
        mask_status = "✓ Present" if results.get('land_sea_mask') else "✗ Failed"
        logger.info(f"Land-sea mask: {mask_status}")
    
    # Temperature statistics summary
    for stat in statistics:
        total = len(results[stat]['success']) + len(results[stat]['failed'])
        success_count = len(results[stat]['success'])
        
        if total == 0:
            logger.info(f"{stat}: All years already existed")
        else:
            logger.info(f"{stat}: {success_count}/{total} successful")
            
            if results[stat]['failed']:
                logger.warning(f"  Failed years: {results[stat]['failed']}")
    
    return results


def main():
    """Main entry point when run as a script."""
    try:
        results = download_all_latest()
        
        # Exit with error code if any downloads failed
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