#!/usr/bin/env python3
"""
ERA5 Climatological Percentile Calculator

Computes percentile thresholds from 30 years (1991-2020) of ERA5 daily
temperature statistics. These thresholds serve as baseline reference values
for detecting extreme temperature events.

The percentiles answer: "What temperature value is exceeded only X% of the time
at each location?" For example, the 99th percentile represents conditions that
occur roughly 3-4 days per year.

Usage:
    # Calculate all missing percentiles
    python make_percentiles.py

    # Or import and use programmatically
    from make_percentiles import calculate_all_percentiles, calculate_percentile
    calculate_all_percentiles()
    calculate_percentile('max', 99.0, years=range(1991, 2021))
"""

import logging, sys
from pathlib import Path
from typing import List, Optional, Set

import xarray as xr

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
STATISTICS = ['min', 'max', 'mean']
DEFAULT_PERCENTILES = [0.95, 0.98, 0.99, 0.995]  # Hot thresholds
COLD_PERCENTILES = [0.01, 0.02, 0.05, 0.005]      # Cold thresholds
REFERENCE_YEARS = range(1991, 2021)  # 30-year climatology period


def get_existing_percentiles(base_dir: Path, stat: str) -> Set[float]:
    """
    Find which percentile files already exist for a given statistic.
    
    Args:
        base_dir: Directory containing percentile NetCDF files
        stat: Temperature statistic ('min', 'max', or 'mean')
        
    Returns:
        Set of percentile values (as floats) that exist on disk
        
    Example:
        >>> get_existing_percentiles(Path('/data/climatology'), 'max')
        {95.0, 99.0, 99.5}
    """
    pattern = f"era5_daily_{stat}_temperature_*pc_1991-2020.nc"
    existing = set()
    
    for p in base_dir.glob(pattern):
        # Extract percentile from filename like "99.0pc"
        try:
            perc_str = p.stem.split('_')[-2].replace('pc', '')
            percentile = float(perc_str)
            existing.add(percentile)
        except (IndexError, ValueError) as e:
            logger.warning(f"Could not parse percentile from {p.name}: {e}")
    
    logger.debug(f"Found {len(existing)} existing percentiles for {stat}")
    return existing


def get_missing_percentiles(
    base_dir: Path,
    stat: str,
    requested_percentiles: List[float]
) -> List[float]:
    """
    Determine which percentile files need to be calculated.
    
    Args:
        base_dir: Directory containing percentile NetCDF files
        stat: Temperature statistic ('min', 'max', or 'mean')
        requested_percentiles: List of percentile values to check (0-1 range)
        
    Returns:
        Sorted list of missing percentiles (converted to 0-100 scale)
    """
    # Convert to percentage scale for comparison with filenames
    requested_pct = {p * 100 for p in requested_percentiles}
    existing_pct = get_existing_percentiles(base_dir, stat)
    missing_pct = sorted(requested_pct - existing_pct)
    
    logger.info(
        f"{stat}: {len(missing_pct)} missing percentiles "
        f"out of {len(requested_pct)} requested"
    )
    return missing_pct


def calculate_percentile(
    stat: str,
    percentile: float,
    input_dir: str = "/data",
    output_dir: str = "/data/climatology",
    years: Optional[range] = None
) -> bool:
    """
    Calculate a single percentile threshold for a temperature statistic.
    
    Loads all years of data using chunked computation to manage memory usage,
    computes the percentile at each grid point across the time dimension,
    and saves the result as a NetCDF file.
    
    Args:
        stat: Temperature statistic ('min', 'max', or 'mean')
        percentile: Percentile value in 0-100 range (e.g., 99.0)
        input_dir: Base directory containing input NetCDF files
        output_dir: Directory for output percentile files
        years: Range of years to include (default: 1991-2020)
        
    Returns:
        True if calculation succeeded, False otherwise
        
    Example:
        >>> calculate_percentile('max', 99.0)
        # Creates: /data/climatology/era5_daily_max_temperature_99.0pc_1991-2020.nc
        
    Note:
        Uses Dask chunked computation to handle large datasets (0.25° × 45 years)
        with limited RAM. Processes in ~700 MB chunks.
    """
    if stat not in STATISTICS:
        raise ValueError(f"stat must be one of {STATISTICS}, got '{stat}'")
    
    if not 0 < percentile <= 100:
        raise ValueError(f"percentile must be in range (0, 100], got {percentile}")
    
    if years is None:
        years = REFERENCE_YEARS
    
    # Set up paths
    stat_dir = Path(input_dir) / stat
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    year_start = min(years)
    year_end = max(years)
    output_file = (
        output_path / 
        f"era5_daily_{stat}_temperature_{percentile}pc_{year_start}-{year_end}.nc"
    )
    
    logger.info(f"Calculating {percentile}th percentile for {stat}")
    logger.info(f"  Years: {year_start}-{year_end}")
    logger.info(f"  Output: {output_file}")
    
    try:
        # Build file list
        files = [
            stat_dir / f"era5_daily_{stat}_temperature_{year}.nc"
            for year in years
        ]
        
        # Check all files exist
        missing_files = [f for f in files if not f.exists()]
        if missing_files:
            logger.error(
                f"Missing {len(missing_files)} input files. "
                f"First missing: {missing_files[0]}"
            )
            return False
        
        logger.info(f"Loading {len(files)} files with chunked computation...")
        # Use chunked loading to manage memory
        # Chunks: ~365 days × 200 lat × 200 lon × 4 bytes ≈ 58 MB per chunk
        ds = xr.open_mfdataset(
            files,
            combine="by_coords",
            chunks={'valid_time': 365, 'latitude': 200, 'longitude': 200},
            parallel=True
        )
        t2m = ds["t2m"]
        
        logger.info(f"Computing {percentile}th percentile (this may take a while)...")
        # Convert percentile to quantile (0-1 range)
        quantile = percentile / 100.0
        
        # Use linear interpolation for faster approximate quantile
        # Good enough for climatological thresholds
        t2m_thresh = t2m.quantile(quantile, dim="valid_time", method='linear')
        
        logger.info("Writing output file...")
        # Stream chunks directly to disk without loading everything
        t2m_thresh.to_netcdf(
            output_file,
            compute=True,
            engine='netcdf4'
        )
        
        logger.info(f"Successfully created {output_file.name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to calculate percentile: {e}", exc_info=True)
        return False
    
def calculate_all_percentiles(
    input_dir: str = "/data",
    output_dir: str = "/data/climatology",
    statistics: Optional[List[str]] = None,
    percentiles: Optional[List[float]] = None
) -> dict:
    """
    Calculate all missing percentile thresholds for temperature statistics.
    
    Scans the output directory for existing percentile files and calculates
    only those that are missing. Processes data from the 30-year reference
    period (1991-2020) by default.
    
    Args:
        input_dir: Base directory containing input NetCDF files
        output_dir: Directory for output percentile files
        statistics: List of statistics to process (default: all)
        percentiles: List of percentile values in 0-1 range (default: standard set)
        
    Returns:
        Dictionary with calculation results:
        {
            'min': {'success': [1.0, 5.0], 'failed': []},
            'max': {'success': [95.0, 99.0], 'failed': []},
            ...
        }
    """
    if statistics is None:
        statistics = STATISTICS
    
    if percentiles is None:
        # Combine hot and cold thresholds
        percentiles = sorted(set(DEFAULT_PERCENTILES + COLD_PERCENTILES))
    
    # Validate inputs
    invalid_stats = set(statistics) - set(STATISTICS)
    if invalid_stats:
        raise ValueError(f"Invalid statistics: {invalid_stats}")
    
    logger.info("=" * 60)
    logger.info("ERA5 Climatological Percentile Calculator")
    logger.info("=" * 60)
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Statistics: {statistics}")
    logger.info(f"Percentiles: {[p*100 for p in percentiles]}")
    
    # Track results
    results = {stat: {'success': [], 'failed': []} for stat in statistics}
    
    # Process each statistic
    for stat in statistics:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find missing percentiles
        missing = get_missing_percentiles(output_path, stat, percentiles)
        
        if not missing:
            logger.info(f"{stat}: All percentiles already exist, skipping")
            continue
        
        logger.info(f"{stat}: Calculating {len(missing)} missing percentiles")
        
        # Calculate each missing percentile
        for perc_pct in missing:
            success = calculate_percentile(
                stat, perc_pct, input_dir, output_dir
            )
            
            if success:
                results[stat]['success'].append(perc_pct)
            else:
                results[stat]['failed'].append(perc_pct)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Calculation Summary")
    logger.info("=" * 60)
    
    for stat in statistics:
        total = len(results[stat]['success']) + len(results[stat]['failed'])
        success_count = len(results[stat]['success'])
        
        if total == 0:
            logger.info(f"{stat}: All percentiles already existed")
        else:
            logger.info(f"{stat}: {success_count}/{total} successful")
            
            if results[stat]['failed']:
                logger.warning(f"  Failed percentiles: {results[stat]['failed']}")
    
    return results


def main():
    """Main entry point when run as a script."""
    try:
        results = calculate_all_percentiles()
        
        # Exit with error code if any calculations failed
        total_failed = sum(len(r['failed']) for r in results.values())
        if total_failed > 0:
            logger.error(f"Completed with {total_failed} failed calculations")
            return 1
        
        logger.info("All percentiles calculated successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Calculation interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())