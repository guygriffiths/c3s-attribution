#!/usr/bin/env python3
"""
ERA5 Climatological Percentile Calculator

Computes percentile thresholds from 30 years (1991-2020) of ERA5 daily
temperature and precipitation statistics. These thresholds serve as baseline
reference values for detecting extreme temperature and precipitation events.

Temperature percentiles answer: "What temperature value is exceeded only X% of
the time at each location?" For example, the 99th percentile represents
conditions that occur roughly 3-4 days per year.

Precipitation percentiles are calculated from wet days only (≥1mm) and include
the 25th, 75th, and 95th percentiles. The IQR (75th - 25th) is used to
normalize precipitation anomalies.

Usage:
    # Calculate all missing percentiles
    python make_percentiles.py

    # Or import and use programmatically
    from make_percentiles import calculate_all_percentiles, calculate_percentile
    calculate_all_percentiles()
    calculate_percentile('max', 99.0, years=range(1991, 2021))
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional, Set

import xarray as xr
import numpy as np

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

# Prevent propagation to root logger (stops duplication)
logger.propagate = False

# Constants
TEMP_STATISTICS = ['min', 'max', 'mean']
PRECIP_STATISTICS = ['tp']  # Total precipitation
ALL_STATISTICS = TEMP_STATISTICS + PRECIP_STATISTICS

TEMP_HOT_PERCENTILES = [0.95, 0.98, 0.99, 0.995]
TEMP_COLD_PERCENTILES = [0.01, 0.02, 0.05, 0.005]
PRECIP_PERCENTILES = [0.25, 0.75, 0.95]  # For IQR and threshold

REFERENCE_YEARS = range(1991, 2021)  # 30-year climatology period
WET_DAY_THRESHOLD = 1.0 * 1e-3  # mm - minimum precipitation to count as "wet day"


def get_existing_percentiles(base_dir: Path, stat: str) -> Set[float]:
	"""
	Find which percentile files already exist for a given statistic.
	
	Args:
		base_dir: Directory containing percentile NetCDF files
		stat: Temperature statistic ('min', 'max', 'mean') or 'tp'
		
	Returns:
		Set of percentile values (as floats) that exist on disk
		
	Example:
		>>> get_existing_percentiles(Path('/data/climatology'), 'max')
		{95.0, 99.0, 99.5}
	"""
	if stat == 'tp':
		pattern = f"era5_daily_tp_*pc_wetdays_1991-2020.nc"
	else:
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
		stat: Statistic ('min', 'max', 'mean', or 'tp')
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
	Calculate a single percentile threshold for a statistic.
	
	For temperature: Loads all years of data and computes percentile at each
	grid point across the time dimension.
	
	For precipitation: Filters to wet days only (≥1mm) before computing
	percentile, since precipitation percentiles are only meaningful for days
	when it actually rains.
	
	Args:
		stat: Statistic ('min', 'max', 'mean' for temp, 'tp' for precip)
		percentile: Percentile value in 0-100 range (e.g., 99.0)
		input_dir: Base directory containing input NetCDF files
		output_dir: Directory for output percentile files
		years: Range of years to include (default: 1991-2020)
		
	Returns:
		True if calculation succeeded, False otherwise
		
	Example:
		>>> calculate_percentile('max', 99.0)
		# Creates: /data/climatology/era5_daily_max_temperature_99.0pc_1991-2020.nc
		
		>>> calculate_percentile('tp', 95.0)
		# Creates: /data/climatology/era5_daily_tp_95.0pc_wetdays_1991-2020.nc
	
	Note:
		Uses Dask chunked computation to handle large datasets (0.25° × 30 years)
		with limited RAM. Processes in chunks to avoid memory issues.
	"""
	if stat not in ALL_STATISTICS:
		raise ValueError(f"stat must be one of {ALL_STATISTICS}, got '{stat}'")
	
	if not 0 < percentile <= 100:
		raise ValueError(f"percentile must be in range (0, 100], got {percentile}")
	
	if years is None:
		years = REFERENCE_YEARS
	
	is_precip = stat == 'tp'
	
	# Set up paths
	if is_precip:
		stat_dir = Path(input_dir) / 'precip'
		var_name = 'tp'
	else:
		stat_dir = Path(input_dir) / stat
		var_name = 't2m'
	
	output_path = Path(output_dir)
	output_path.mkdir(parents=True, exist_ok=True)
	
	year_start = min(years)
	year_end = max(years)
	
	if is_precip:
		output_file = (
			output_path / 
			f"era5_daily_tp_{percentile}pc_wetdays_{year_start}-{year_end}.nc"
		)
	else:
		output_file = (
			output_path / 
			f"era5_daily_{stat}_temperature_{percentile}pc_{year_start}-{year_end}.nc"
		)
	
	logger.info(f"Calculating {percentile}th percentile for {stat}")
	logger.info(f"  Years: {year_start}-{year_end}")
	logger.info(f"  Output: {output_file}")
	
	try:
		# Build file list
		if is_precip:
			files = [
				stat_dir / f"era5_daily_tp_{year}.nc"
				for year in years
			]
		else:
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
		
		logger.info(f"Loading {len(files)} files...")
		
		# Use chunked loading to manage memory
		ds = xr.open_mfdataset(
			files,
			combine="by_coords",
			chunks='auto',
			parallel=True
		)
		
		data = ds[var_name]
		
		logger.info(f"Data shape: {data.shape}")
		
		# For precipitation, filter to wet days only
		if is_precip:
			logger.info(f"Filtering to wet days (≥{WET_DAY_THRESHOLD}mm)...")
			# Convert from m to mm if needed
			if data.max() < 1:  # Data likely in meters
				data = data * 1000
				logger.info("Converted precipitation from m to mm")
			
			# Mask dry days
			wet_mask = data >= WET_DAY_THRESHOLD
			data_wet = data.where(wet_mask)
			
			logger.info(f"Computing {percentile}th percentile of wet days...")
			quantile = percentile / 100.0
			result = data_wet.quantile(quantile, dim='valid_time', skipna=True)
		else:
			logger.info(f"Computing {percentile}th percentile...")
			quantile = percentile / 100.0
			result = data.quantile(quantile, dim='valid_time')
		
		# Convert to dataset with proper variable name
		ds_out = result.to_dataset(name=var_name)
		
		logger.info("Writing to disk...")
		ds_out.to_netcdf(output_file)
		
		logger.info(f"Successfully created {output_file.name}")
		return True
		
	except Exception as e:
		logger.error(f"Failed to calculate percentile: {e}", exc_info=True)
		return False


def calculate_all_percentiles(
	input_dir: str = "/data",
	output_dir: str = "/data/climatology",
	statistics: Optional[List[str]] = None,
	temp_percentiles: Optional[List[float]] = None,
	precip_percentiles: Optional[List[float]] = None
) -> dict:
	"""
	Calculate all missing percentile thresholds for temperature and precipitation.
	
	Scans the output directory for existing percentile files and calculates
	only those that are missing. Processes data from the 30-year reference
	period (1991-2020) by default.
	
	Temperature percentiles are computed from all days.
	Precipitation percentiles are computed from wet days only (≥1mm).
	
	Args:
		input_dir: Base directory containing input NetCDF files
		output_dir: Directory for output percentile files
		statistics: List of statistics to process (default: all)
		temp_percentiles: Percentile values for temperature (0-1 range)
		precip_percentiles: Percentile values for precipitation (0-1 range)
		
	Returns:
		Dictionary with calculation results:
		{
			'min': {'success': [1.0, 5.0], 'failed': []},
			'max': {'success': [95.0, 99.0], 'failed': []},
			'tp': {'success': [25.0, 75.0, 95.0], 'failed': []},
			...
		}
	"""
	if statistics is None:
		statistics = ALL_STATISTICS
	
	if temp_percentiles is None:
		# Combine hot and cold thresholds
		temp_percentiles = sorted(set(TEMP_HOT_PERCENTILES + TEMP_COLD_PERCENTILES))
	
	if precip_percentiles is None:
		precip_percentiles = PRECIP_PERCENTILES
	
	# Validate inputs
	invalid_stats = set(statistics) - set(ALL_STATISTICS)
	if invalid_stats:
		raise ValueError(f"Invalid statistics: {invalid_stats}")
	
	logger.info("=" * 60)
	logger.info("ERA5 Climatological Percentile Calculator")
	logger.info("=" * 60)
	logger.info(f"Input directory: {input_dir}")
	logger.info(f"Output directory: {output_dir}")
	logger.info(f"Statistics: {statistics}")
	logger.info(f"Temperature percentiles: {[p*100 for p in temp_percentiles]}")
	logger.info(f"Precipitation percentiles: {[p*100 for p in precip_percentiles]}")
	
	# Track results
	results = {stat: {'success': [], 'failed': []} for stat in statistics}
	
	# Process each statistic
	for stat in statistics:
		output_path = Path(output_dir)
		output_path.mkdir(parents=True, exist_ok=True)
		
		# Determine which percentiles to use
		if stat == 'tp':
			percentiles = precip_percentiles
		else:
			percentiles = temp_percentiles
		
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