#!/usr/bin/env python3

# Standard library imports
import json
import math
import os
import logging, sys
import pickle
import warnings
from collections import deque, namedtuple
from typing import List, Tuple, Union, Optional

# Third-party imports
import alphashape
import numpy as np
import pandas as pd
import xarray as xr
from scipy.sparse import coo_matrix
from shapely.geometry import MultiPoint, MultiPolygon, Polygon
from shapely.ops import unary_union
from sklearn.cluster import DBSCAN

# Local imports (if any)
# from .module import something

# ============================================================================
# Constants
# ============================================================================

# Mean Earth radius in kilometers
R = 6371.0088
WET_DAY_THRESHOLD = 1.0 * 1e-3  # 1mm in meters - minimum precipitation for "wet day"

# ============================================================================
# Distance and Geometry Calculations
# ============================================================================

def haversine_fast(ll1: Tuple[float, float], ll2: Tuple[float, float]) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    
    Uses the Haversine formula to compute distance in kilometers between
    two lat/lon coordinate pairs.
    
    Args:
        ll1: First point as (latitude, longitude) in degrees
        ll2: Second point as (latitude, longitude) in degrees
        
    Returns:
        Distance in kilometers
        
    Example:
        >>> haversine_fast((51.5074, -0.1278), (48.8566, 2.3522))  # London to Paris
        334.57...
    """
    # Convert degrees to radians
    lat1, lon1 = map(math.radians, ll1)
    lat2, lon2 = map(math.radians, ll2)
    
    # Differences
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Haversine formula
    a = (math.sin(dlat * 0.5)**2 + 
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon * 0.5)**2)
    
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def safe_alphashape(
    points: np.ndarray,
    alpha: float = 1.0,
    max_attempts: int = 5,
    growth: float = 2.0,
    fallback_buffer: float = 0.125
) -> Optional[Union[Polygon, MultiPolygon]]:
    """
    Compute an alpha shape (concave hull) with automatic fallbacks.
    
    Attempts to create an alpha shape with progressively looser alpha values
    if initial attempts fail. Falls back to buffered geometries for degenerate
    cases (single point, line, or when alpha shape consistently fails).
    
    Args:
        points: Array of coordinates, shape (N, 2) with columns [lat, lon]
        alpha: Initial alpha parameter (smaller = tighter fit)
        max_attempts: Number of times to retry with increased alpha
        growth: Factor to multiply alpha by on each retry
        fallback_buffer: Buffer size in degrees for fallback geometries
        
    Returns:
        Shapely Polygon/MultiPolygon or None if input is empty
        
    Note:
        Handles longitude wraparound by converting negative longitudes to 0-360
        range when the span exceeds 180 degrees.
    """
    if points is None or len(points) == 0:
        return None
    
    # Handle longitude wraparound for global datasets
    longitude_span = points[:, 1].max() - points[:, 1].min()
    if longitude_span > 180:
        points = points.copy()
        points[:, 1] = np.where(
            points[:, 1] < 0, points[:, 1] + 360, points[:, 1]
        )

    # Try progressively looser alpha values
    for i in range(max_attempts):
        try:
            shape = alphashape.alphashape(points, alpha)
            if shape and not shape.is_empty:
                return shape
        except Exception:
            pass
        alpha *= growth

    # Fallback strategies for degenerate cases
    n = len(points)
    
    if n == 1:
        # Single point: create small square around it
        x, y = points[0]
        return Polygon([
            (x - fallback_buffer, y - fallback_buffer),
            (x + fallback_buffer, y - fallback_buffer),
            (x + fallback_buffer, y + fallback_buffer),
            (x - fallback_buffer, y + fallback_buffer),
        ])
    
    elif n == 2:
        # Two points: create buffered line
        return MultiPoint(points).buffer(fallback_buffer)
    
    else:
        # Multiple points: use buffered convex hull
        mp = MultiPoint(points)
        convex = mp.convex_hull
        
        if convex.is_empty:
            return None
        
        # Scale buffer size to point spread
        x_vals, y_vals = zip(*points)
        spread = max(max(x_vals) - min(x_vals), max(y_vals) - min(y_vals))
        buffer_size = min(fallback_buffer, spread * 0.05)
        
        return convex.buffer(buffer_size)


def get_region(shape: Union[Polygon, MultiPolygon]) -> List[List[List[float]]]:
    """
    Extract coordinate lists from Shapely geometries for serialization.
    
    Converts Polygon or MultiPolygon geometries into nested coordinate lists
    suitable for GeoJSON or other serialization formats. For non-polygon types,
    creates a padded bounding box.
    
    Args:
        shape: Shapely Polygon or MultiPolygon geometry
        
    Returns:
        List of polygons, where each polygon is a list of [lon, lat] coordinate pairs
        
    Example:
        For a simple polygon: [[[lon1, lat1], [lon2, lat2], ...]]
        For a multipolygon: [[[lon1, lat1], ...], [[lon3, lat3], ...]]
    """
    if shape is None:
        return []

    if shape.geom_type == "Polygon":
        return [[[x, y] for x, y in shape.exterior.coords]]
    
    elif shape.geom_type == "MultiPolygon":
        # Try to merge into single polygon
        merged = unary_union(shape)
        if merged.geom_type == "Polygon":
            return [[[x, y] for x, y in merged.exterior.coords]]
        else:
            # Still multiple polygons after merge
            return [
                [[x, y] for x, y in poly.exterior.coords]
                for poly in merged.geoms
            ]
    
    else:
        # Fallback: create padded bounding box
        minx, miny, maxx, maxy = shape.bounds
        pad = 0.125
        square = [
            [minx - pad, miny - pad],
            [minx - pad, maxy + pad],
            [maxx + pad, maxy + pad],
            [maxx + pad, miny - pad],
            [minx - pad, miny - pad],
        ]
        return [square]


# ============================================================================
# Clustering
# ============================================================================

def walk_scan(
    D_coo: coo_matrix,
    eps: float,
    min_samples: int = 1
) -> np.ndarray:
    """
    Sparse distance-matrix DBSCAN implementation.
    
    A memory-efficient clustering algorithm for sparse distance matrices.
    Uses a breadth-first search approach to grow clusters from seed points,
    requiring only the sparse distance matrix rather than full pairwise distances.
    
    Args:
        D_coo: Sparse COO matrix of pairwise distances (only store distances < threshold)
        eps: Maximum distance for two points to be considered neighbors
        min_samples: Minimum cluster size; smaller clusters are marked as noise
        
    Returns:
        Array of cluster labels (0, 1, 2, ...) with -1 for noise points
        
    Algorithm:
        1. For each unvisited point, find neighbors within eps distance
        2. If enough neighbors exist, start a new cluster and expand via BFS
        3. Mark clusters smaller than min_samples as noise (-1)
        
    Note:
        This is optimized for cases where most point pairs are too far apart
        to be neighbors, making a sparse matrix representation efficient.
    """
    D = D_coo.tocsr()
    n_points = D.shape[0]
    
    visited = np.zeros(n_points, dtype=bool)
    labels = -np.ones(n_points, dtype=int)
    cluster_id = 0

    for i in range(n_points):
        if visited[i]:
            continue

        # Find neighbors within eps distance
        neighbours = D[i].indices[D[i].data <= eps]

        # Initialize cluster expansion queue
        queue = deque([i])
        queue.extend(neighbours)
        cluster_members = set()

        # Breadth-first search to grow cluster
        while queue:
            point = queue.popleft()
            if visited[point]:
                continue
            
            visited[point] = True
            cluster_members.add(point)

            # Expand cluster if point has enough neighbors
            neighbours = D[point].indices[D[point].data <= eps]
            if len(neighbours) >= min_samples:
                queue.extend(neighbours)

        # Only keep clusters that meet minimum size requirement
        if len(cluster_members) >= min_samples:
            for pt in cluster_members:
                labels[pt] = cluster_id
            cluster_id += 1

    return labels


# ============================================================================
# Serialization and Formatting
# ============================================================================

def format_time(t: Union[np.datetime64, pd.Timestamp, str]) -> str:
    """
    Format various time types to ISO 8601 string with 'Z' suffix.
    
    Args:
        t: Time value (numpy datetime64, pandas Timestamp, or string)
        
    Returns:
        ISO 8601 formatted string with 'Z' timezone indicator
        
    Raises:
        ValueError: If time type is not supported
    """
    if isinstance(t, np.datetime64):
        return np.datetime_as_string(t, unit="s") + "Z"
    elif isinstance(t, pd.Timestamp):
        return t.isoformat() + "Z"
    elif isinstance(t, str):
        return t + "Z"
    else:
        raise ValueError(f"Unsupported time type: {type(t)}")


def to_serializable(obj):
    """
    Recursively convert NumPy types to Python native types for JSON serialization.
    
    Handles numpy arrays, scalars, and nested structures (lists, dicts, sets).
    Essential for converting scientific computing types to JSON-safe format.
    
    Args:
        obj: Object to convert (can be nested structure)
        
    Returns:
        JSON-serializable equivalent of the input
        
    Example:
        >>> to_serializable(np.array([1, 2, 3]))
        [1, 2, 3]
        >>> to_serializable({'data': np.float32(1.5)})
        {'data': 1.5}
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        v = float(obj)
        return None if math.isnan(v) or math.isinf(v) else v
    elif isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, (list, tuple)):
        return [to_serializable(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    else:
        return obj


def round_floats(obj, decimals: int = 4):
    """
    Recursively round floating-point numbers in nested structures.
    
    Useful for reducing file sizes and improving readability of coordinate
    data and other floating-point values in output files.
    
    Args:
        obj: Object to process (can be nested dict/list structure)
        decimals: Number of decimal places to round to (default: 4)
        
    Returns:
        Structure with rounded floats
    """
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else round(obj, decimals)
    elif isinstance(obj, dict):
        return {k: round_floats(v, decimals) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [round_floats(x, decimals) for x in obj]
    else:
        return obj


# ============================================================================
# ID Generation
# ============================================================================
def get_id(eventtype: str, event: 'Eventlet') -> str:
    """
    Generate a unique, human-readable ID for an event based on its peak pixel.
    
    The ID encodes the peak pixel's properties: event type, date, location, and value.
    The peak pixel is defined differently based on event type:
    - For "hot" or "wet" events: pixel with MAXIMUM temperature value
    - For "cold" or "dry" events: pixel with MINIMUM value
    
    Ties are broken by: (1) earliest time, (2) lowest latitude, (3) lowest longitude.
    
    This approach ensures:
    - Same event in different datasets (e.g., different processing parameters) gets same ID
    - Enables matching equivalent events across attribution studies
    - Human-readable and sortable by date
    
    Args:
        eventtype: Event type ("hot", "cold", "wet", etc.)
        event: Eventlet object containing time slices, coordinates, and values
        
    Returns:
        Formatted ID string with structure:
        {type}{YYYYMMDD}{value_code:04d}{lat:06d}{lon:06d}
        
    Example:
        >>> event = Eventlet(...)  # Hot event
        >>> get_id("hot", event)
        'hot20240715400051505359875'
        
    Notes:
        - Coordinates are snapped to 0.001° precision (grid resolution)
        - Temperature events: value encoded as Celsius × 10 (e.g., 40.0°C → 400)
          Negative temperatures encoded as (1000 + abs(val)) (e.g., -10°C → 1100)
        - Wet events: value encoded as IQR anomaly × 100 (e.g., 2.50 IQRs → 250)
          This is dimensionless and always positive, so no negative handling needed
        - Location coordinates shifted to positive range for consistent formatting
        - Value code clamped to 4 digits (max 9999) in all cases
        
    Peak pixel selection:
        1. Find pixel with extreme value (max for hot/wet, min for cold/dry)
        2. If tied, use earliest occurrence (first time slice)
        3. If still tied, use lowest latitude
        4. If still tied, use lowest longitude
    """
    # Collect all coordinates and values across all time slices
    all_coords = []
    all_values = []
    all_times = []
    
    for i, (time_slice, coords_slice, values_slice) in enumerate(
        zip(event.times, event.slices, event.values)
    ):
        for coord, value in zip(coords_slice, values_slice):
            all_coords.append(coord)
            all_values.append(value)
            all_times.append(time_slice)
    
    # Convert to numpy arrays for easier manipulation
    all_coords = np.array(all_coords)  # Shape: (N, 2) - [lat, lon]
    all_values = np.array(all_values)  # Shape: (N,)
    all_times = np.array(all_times)    # Shape: (N,)
    
    # Determine whether to find max or min based on event type
    if eventtype.lower() in ['cold', 'dry']:
        # For cold/drought events, find minimum value
        extreme_value = np.min(all_values)
        extreme_indices = np.where(all_values == extreme_value)[0]
    else:
        # For hot/wet events (and default), find maximum value
        extreme_value = np.max(all_values)
        extreme_indices = np.where(all_values == extreme_value)[0]
    
    # Apply tie-breaking rules
    if len(extreme_indices) == 1:
        peak_idx = extreme_indices[0]
    else:
        # Tie-breaking: earliest time, then lowest lat, then lowest lon
        candidates = extreme_indices
        
        # 2. Among tied values, find earliest time
        min_time = np.min(all_times[candidates])
        candidates = candidates[all_times[candidates] == min_time]
        
        if len(candidates) == 1:
            peak_idx = candidates[0]
        else:
            # 3. Among tied times, find lowest latitude
            min_lat = np.min(all_coords[candidates, 0])
            candidates = candidates[all_coords[candidates, 0] == min_lat]
            
            if len(candidates) == 1:
                peak_idx = candidates[0]
            else:
                # 4. Among tied latitudes, find lowest longitude
                min_lon = np.min(all_coords[candidates, 1])
                peak_idx = candidates[all_coords[candidates, 1] == min_lon][0]
    
    # Extract peak pixel properties
    peak_time = all_times[peak_idx]
    peak_lat, peak_lon = all_coords[peak_idx]
    peak_value = all_values[peak_idx]
    
    # Snap location to 0.001° precision
    lat = round(float(peak_lat), 3)
    lon = round(float(peak_lon), 3)
    
    # Shift coordinates to positive range for fixed-width encoding
    lat_code = int(round((lat + 90) * 1000))   # Range: 0 to 180000
    lon_code = int(round((lon + 180) * 1000))  # Range: 0 to 360000
    
    # Encode peak value in a type-appropriate way
    if eventtype.lower() == 'wet':
        # Anomaly is dimensionless (IQR multiples); encode as anomaly × 100
        # e.g. 1.50 IQRs → 150, 3.25 IQRs → 325
        value_code = int(round(abs(float(peak_value)) * 100))
    else:
        # Temperature: convert from Kelvin to Celsius × 10
        # e.g. 40.0°C → 400; negative temps encoded above 1000 (e.g. -10°C → 1100)
        temp_celsius = float(peak_value) - 273.15
        value_code = int(round(temp_celsius * 10))
        if value_code < 0:
            value_code = 1000 + abs(value_code)
    value_code = min(value_code, 9999)
    
    # Format: TYPE + DATE(8) + VALUE(4) + LAT(6) + LON(6)
    # Total: variable prefix + 24 fixed digits
    return (
        f"{eventtype}{pd.Timestamp(peak_time).strftime('%Y%m%d')}"
        f"{value_code:04d}{lat_code:06d}{lon_code:06d}"
    )
# ============================================================================
# Data Loading and Transformation
# ============================================================================

def load_data(
    data_path: str,
    ref_path: str,
    ref_path_p75: Optional[str] = None,
    ref_path_p25: Optional[str] = None,
    land_sea_mask_path: Optional[str] = None
) -> Tuple[xr.DataArray, xr.DataArray, Optional[xr.DataArray], Optional[xr.DataArray], Optional[xr.DataArray]]:
    """
    Load and preprocess NetCDF climate data files.
    
    Opens multiple data files (temperature/precipitation, references, land-sea mask)
    and standardizes longitude coordinates to -180 to +180 range.
    
    Args:
        data_path: Path or glob pattern for main data (t2m or tp)
        ref_path: Path to reference/threshold dataset
        ref_path_p75: Path to 75th percentile (for precip IQR, optional)
        ref_path_p25: Path to 25th percentile (for precip IQR, optional)
        land_sea_mask_path: Path to land-sea mask file (optional)
        
    Returns:
        Tuple of (data, ref_data, ref_p75, ref_p25, land_sea_mask)
        where ref_p75, ref_p25, and land_sea_mask may be None
    """
    # Open datasets
    logger.info(f"{data_path}, {ref_path}")
    ds = xr.open_mfdataset(data_path)
    ref = xr.open_dataset(ref_path)
    
    ref_p75 = xr.open_dataset(ref_path_p75) if ref_path_p75 else None
    ref_p25 = xr.open_dataset(ref_path_p25) if ref_path_p25 else None
    
    if land_sea_mask_path:
        land_sea_mask = xr.open_dataset(land_sea_mask_path)
    else:
        land_sea_mask = None

    def shift_longitudes(da: xr.DataArray) -> xr.DataArray:
        """Shift longitude coords from [0, 360) to [-180, 180) and sort."""
        da = da.assign_coords(longitude=(((da.longitude + 180) % 360) - 180))
        return da.sortby("longitude")

    # Determine variable name (t2m or tp)
    var_name = 't2m' if 't2m' in ds else 'tp'
    
    # Apply longitude transformation to all datasets
    data = shift_longitudes(ds[var_name])
    ref_data = shift_longitudes(ref[var_name])
    ref_p75_data = shift_longitudes(ref_p75[var_name]) if ref_p75 else None
    ref_p25_data = shift_longitudes(ref_p25[var_name]) if ref_p25 else None
    lsm_data = (shift_longitudes(land_sea_mask["lsm"]) 
                if land_sea_mask is not None else None)
    
    return data, ref_data, ref_p75_data, ref_p25_data, lsm_data


# ============================================================================
# Multiprocessing Helpers
# ============================================================================

def downstream_worker(q, clusterer):
    """
    Worker function for multiprocessing event processing.
    
    Continuously processes eventlets from a queue until receiving a shutdown
    signal (None). Used for parallel processing of detected events.
    
    Args:
        q: Queue containing Eventlet objects to process
        clusterer: EventletFactory or similar object with process_eventlet method
        
    Note:
        Blocks waiting for queue items. Send None to signal shutdown.
    """
    while True:
        ev = q.get()
        if ev is None:
            break  # Shutdown signal received
        
        clusterer.process_eventlet(ev)
        q.task_done()

class Eventlet:
    """
    Represents a spatiotemporal event tracked across multiple time slices.
    
    An Eventlet stores coordinate data (lat/lon pairs) and associated values
    at different time points, allowing tracking of features like weather systems,
    pollution plumes, or other geographic phenomena over time.
    """
    
    def __init__(self, time, coords, values):
        """
        Initialize an Eventlet with data from a single time point.
        
        Args:
            time: Timestamp for this initial observation
            coords: List of (lat, lon) tuples or NumPy array of shape (N, 2)
            values: Array of values associated with each coordinate point
        """
        self.times = [time]
        # Expecting coords as a list of (lat, lon) tuples or a NumPy array
        self.slices = [np.array(coords, dtype=np.float32)]  # list of (N, 2) arrays
        self.values = [values]

    def last_time(self):
        """
        Get the most recent timestamp in this eventlet.
        
        Returns:
            The latest time point in the eventlet's history
        """
        return self.times[-1]

    def earliest_time(self):
        """
        Get the earliest timestamp in this eventlet.
        
        Returns:
            The first time point in the eventlet's history
        """
        return self.times[0]

    def centroid(self, n):
        """
        Calculate the geographic centroid of the eventlet at a specific time slice.
        
        Args:
            n: Index of the time slice (uses last slice if n >= len(slices))
            
        Returns:
            Tuple of (lat_mean, lon_mean) or None if no data exists
        """
        if not self.slices:
            return None
        target_slice = self.slices[n] if n < len(self.slices) else self.slices[-1]
        if len(target_slice) == 0:
            return None
        lat_mean = np.mean(target_slice[:, 0])
        lon_mean = np.mean(target_slice[:, 1])
        return (lat_mean, lon_mean)

    def hull(self, n, alpha=1.0):
        """
        Generate an alpha shape (concave hull) around the points at time slice n.
        
        Args:
            n: Index of the time slice
            alpha: Alpha parameter controlling hull tightness (default 1.0)
            
        Returns:
            Alpha shape geometry or None if insufficient data
        """
        if not self.slices:
            return None
        target_slice = self.slices[n] if n < len(self.slices) else self.slices[-1]
        if len(target_slice) == 0:
            return None

        return safe_alphashape(target_slice, alpha)

    def overlaps(self, coords, time, eps=1e-6):
        """
        Check if any of the provided coordinates overlap with the eventlet's current slice.
        
        Uses distance threshold (eps) to determine if points are close enough to be
        considered overlapping.
        
        Args:
            coords: Array of (lat, lon) coordinates to test, shape (N, 2)
            eps: Distance threshold for considering points as overlapping (default 1e-6)
            
        Returns:
            True if any points are within eps distance of current slice points
        """
        test = np.array(coords, dtype=np.float32)  # shape (N, 2)
        idx = (self.times.index(time) - 1) if (time in self.times) and (self.times.index(time) > 0) else -1
        current = self.slices[idx]  # shape (M, 2)

        # Compute pairwise absolute differences for lat and lon
        # Broadcast shapes: (N,1,2) and (1,M,2) -> (N,M,2)
        diffs = np.abs(test[:, None, :] - current[None, :, :])

        # Check if differences in both lat & lon are < eps
        close_points = np.all(diffs < eps, axis=2)  # shape (N, M), True if points close

        # Check if any pair is close
        return np.any(close_points)

    def extend(self, time, coords, values):
        """
        Add new coordinate data to the eventlet at a given time.
        
        If the time already exists, appends to that time slice. Otherwise creates
        a new time slice. Maintains chronological ordering of all slices.
        
        Args:
            time: Timestamp for the new data
            coords: Coordinates to add, shape (N, 2)
            values: Values associated with the coordinates
        """
        coords_arr = np.array(coords, dtype=np.float32)
        values_arr = np.array(values, dtype=np.float32)
        
        if time in self.times:
            # Append to existing time slice
            idx = self.times.index(time)
            self.slices[idx] = np.vstack((self.slices[idx], coords_arr))
            self.values[idx] = np.concatenate((self.values[idx], values_arr))
        else:
            # Create new time slice
            self.times.append(time)
            self.slices.append(coords_arr)
            self.values.append(values_arr)

        # Keep times + slices sorted chronologically
        sorted_triplets = sorted(
            zip(self.times, self.slices, self.values), key=lambda x: x[0]
        )
        self.times, self.slices, self.values = map(list, zip(*sorted_triplets))

    def merge(self, other):
        """
        Merge another Eventlet into this one, combining all time slices.
        
        For overlapping time points, concatenates the coordinate arrays.
        Maintains chronological ordering after merge.
        
        Args:
            other: Another Eventlet instance to merge into this one
        """
        # Build lookup for existing times
        time_to_idx = {t: i for i, t in enumerate(self.times)}

        for t, other_slice, other_val in zip(other.times, other.slices, other.values):
            if t in time_to_idx:
                # Merge into existing time slice
                i = time_to_idx[t]
                self.slices[i] = np.vstack((self.slices[i], other_slice))
                self.values[i] = np.concatenate((self.values[i], other_val))
            else:
                # Add new time slice
                self.times.append(t)
                self.slices.append(other_slice.copy())
                self.values.append(other_val.copy())

        # Re-sort all three by time
        sorted_triplets = sorted(
            zip(self.times, self.slices, self.values), key=lambda x: x[0]
        )
        self.times, self.slices, self.values = map(list, zip(*sorted_triplets))

    def is_expired(self, oldest_upstream_time, time_threshold):
        """
        Check if this eventlet has expired based on a time threshold.
        
        An eventlet is expired if its last observation plus the threshold
        is earlier than the oldest upstream time being processed.
        
        Args:
            oldest_upstream_time: The oldest time currently being processed
            time_threshold: How long after last observation before expiry.
                            Integers are interpreted as days; strings like "1D"
                            or "12H" are also accepted.
            
        Returns:
            True if the eventlet has expired
        """
        if isinstance(time_threshold, (int, float)):
            td = pd.Timedelta(days=time_threshold)
        else:
            td = pd.Timedelta(time_threshold)
        return (self.last_time() + td) < oldest_upstream_time

    def is_valid(self, min_time_steps, min_mean_pixels):
        """
        Check if the eventlet meets minimum validity requirements.
        
        An eventlet is valid if it has at least min_length time slices AND
        the last slice contains at least min_length points.
        
        Args:
            min_length: Minimum number of slices and points required
            
        Returns:
            True if the eventlet meets validity criteria
        """
        # Check if the eventlet has enough slices
        if len(self.slices) < min_time_steps:
            return False
        # Check if the last slice has enough points
        total_pixels = 0
        for sl in self.slices:
            total_pixels += len(sl)
        if total_pixels / len(self.slices) < min_mean_pixels:
            return False
        return True

    def clear(self):
        """
        Remove all data from the eventlet, clearing times and slices.
        """
        self.times.clear()
        self.slices.clear()

    def remove_ocean(self, land_sea_mask):
        """
        Filter out ocean points from all time slices, keeping only land points.
        
        Uses a land-sea mask dataset to identify which coordinates fall on land.
        Removes any slices that become empty after filtering.
        
        Args:
            land_sea_mask: xarray Dataset with latitude, longitude, and mask values
                          (0 = ocean, non-zero = land)
        """
        if land_sea_mask is None:
            return

        # Check if latitude is in ascending order and prepare for searchsorted
        lat_asc = np.all(np.diff(land_sea_mask.latitude) > 0)
        lats = land_sea_mask.latitude.values
        if not lat_asc:
            lats = lats[::-1]  # ascending for searchsorted

        for i in range(len(self.slices)):
            if self.hull(i) is not None:
                coords = np.array(self.slices[i])
                
                # Find latitude indices using binary search
                lat_indices = np.searchsorted(lats, coords[:, 0])
                lat_indices = np.clip(
                    lat_indices, 0, land_sea_mask.latitude.size - 1
                )
                if not lat_asc:
                    lat_indices = land_sea_mask.latitude.size - 1 - lat_indices

                # Find longitude indices using binary search
                lon_indices = np.searchsorted(land_sea_mask.longitude, coords[:, 1])
                lon_indices = np.clip(
                    lon_indices, 0, land_sea_mask.longitude.size - 1
                )

                # Look up mask values and keep only land points (non-zero)
                mask_values = land_sea_mask.values[0, lat_indices, lon_indices]
                land_points = mask_values != 0

                self.slices[i] = coords[land_points]
                self.values[i] = np.array(self.values[i])[land_points]

        # Remove any empty slices that resulted from filtering
        # non_empty_indices = [i for i in range(len(self.slices)) if len(self.slices[i]) > 0]
        # self.times = [self.times[i] for i in non_empty_indices]
        # self.slices = [self.slices[i] for i in non_empty_indices]
        # self.values = [self.values[i] for i in non_empty_indices]

    def remove_land(self, land_sea_mask):
        """
        Filter out land points from all time slices, keeping only ocean points.
        
        Uses a land-sea mask dataset to identify which coordinates fall on ocean.
        Removes any slices that become empty after filtering.
        
        Args:
            land_sea_mask: xarray Dataset with latitude, longitude, and mask values
                          (1 = land, non-1 = ocean)
        """
        if land_sea_mask is None:
            return

        # Check if latitude is in ascending order and prepare for searchsorted
        lat_asc = np.all(np.diff(land_sea_mask.latitude) > 0)
        lats = land_sea_mask.latitude.values
        if not lat_asc:
            lats = lats[::-1]  # ascending for searchsorted

        for i in range(len(self.slices)):
            if self.hull(i) is not None:
                coords = np.array(self.slices[i])
                
                # Find latitude indices using binary search
                lat_indices = np.searchsorted(lats, coords[:, 0])
                lat_indices = np.clip(
                    lat_indices, 0, land_sea_mask.latitude.size - 1
                )
                if not lat_asc:
                    lat_indices = land_sea_mask.latitude.size - 1 - lat_indices

                # Find longitude indices using binary search
                lon_indices = np.searchsorted(land_sea_mask.longitude, coords[:, 1])
                lon_indices = np.clip(
                    lon_indices, 0, land_sea_mask.longitude.size - 1
                )

                # Look up mask values and keep only ocean points (non-1)
                mask_values = land_sea_mask.values[0, lat_indices, lon_indices]
                ocean_points = mask_values != 1

                self.slices[i] = coords[ocean_points]
                self.values[i] = np.array(self.values[i])[ocean_points]

        # Remove any empty slices that resulted from filtering
        non_empty_indices = [i for i in range(len(self.slices)) if len(self.slices[i]) > 0]
        self.times = [self.times[i] for i in non_empty_indices]
        self.slices = [self.slices[i] for i in non_empty_indices]
        self.values = [self.values[i] for i in non_empty_indices]

"""
EventletFactory class for detecting and tracking spatiotemporal events in climate data.

This class implements a sophisticated event detection and tracking system that:
1. Identifies regions exceeding (or below) thresholds in gridded data
2. Clusters nearby points using spatial distance metrics
3. Tracks events across time slices
4. Expires old events and finalizes completed ones
5. Outputs detailed event metadata and geometries
"""

class EventletFactory:
    """
    Factory for detecting, tracking, and managing spatiotemporal events.
    
    The EventletFactory processes gridded climate/weather data time slice by time slice,
    identifying regions that exceed thresholds, clustering nearby points, and tracking
    how these clusters evolve over time. When events expire or the run completes,
    it generates comprehensive metadata including geometries, statistics, and time series.
    
    Key responsibilities:
    - Threshold detection with persistence filtering (temperature only)
    - Spatial clustering of threshold-exceeding points
    - Temporal tracking of clusters across time slices
    - Event lifecycle management (creation, extension, expiration)
    - Output generation in JSON format
    
    Attributes:
        data: xarray DataArray with temperature/precipitation/variable data
        threshold: Numeric threshold value for event detection (temperature only)
        over_threshold: If True, detect values > threshold; if False, detect values < threshold
        ref_data: Reference/threshold data
        ref_p75: 75th percentile reference (for precipitation IQR)
        ref_p25: 25th percentile reference (for precipitation IQR)
        land_sea_mask: Optional mask to filter land/ocean points
        expiry_days: Days without new data before an event expires
        min_length: Minimum number of time slices for a valid event
        min_samples: Minimum cluster size for DBSCAN
        radius: Maximum distance (km) for points to be neighbors
        active: List of currently active Eventlet objects
        output_queue: Queue of finalized events ready for output
        output_path: Directory path for output files
        use_dbscan: If True, use sklearn DBSCAN; if False, use custom walk_scan
        eventtype: Event type label (e.g., 'hot', 'cold', 'wet')
        land_only: If True, only track events over land
        ocean_only: If True, only track events over ocean
    """
    
    def __init__(
        self,
        data,
        ref_data,
        ref_p75=None,
        ref_p25=None,
        threshold=None,
        over_threshold=True,
        land_sea_mask=None,
        expiry_days=1,
        min_length=3,
        neighbor_radius=200,
        min_samples=1,
        output_path="/data/output-debug/events",
        use_dbscan=False,
        last_slice_name=None,
        eventtype='hot',
        land_only=False,
        ocean_only=False
    ):
        """
        Initialize the EventletFactory with data and configuration parameters.
        
        For precipitation: Uses IQR normalization, no persistence requirement
        For temperature: Uses absolute threshold + persistence filtering
        
        Args:
            data: xarray DataArray with dimensions (time, latitude, longitude)
            ref_data: Reference/threshold data with same dimensions as data
            ref_p75: 75th percentile reference (for precip IQR calculation)
            ref_p25: 25th percentile reference (for precip IQR calculation)
            threshold: Threshold value for event detection (e.g., temperature in Kelvin)
            over_threshold: If True, detect values > threshold; otherwise < threshold
            land_sea_mask: Optional xarray DataArray with land-sea mask (1=land, 0=ocean)
            expiry_days: Number of days without updates before event expires
            min_length: Minimum time slices required for valid event (ignored for precip)
            neighbor_radius: Maximum distance (km) for spatial clustering
            min_samples: Minimum cluster size for DBSCAN/walk_scan
            output_path: Directory path for output files
            use_dbscan: If True, use sklearn DBSCAN instead of custom walk_scan
            last_slice_name: Optional filename with previous run state for resumption
            eventtype: Event type label for output (e.g., 'hot', 'cold', 'wet')
            land_only: If True, only track events over land (removes ocean points)
            ocean_only: If True, only track events over ocean (removes land points)
        """
        # Store configuration
        self.data = data
        self.threshold = threshold
        self.over_threshold = over_threshold
        self.ref_data = ref_data
        self.ref_p75 = ref_p75
        self.ref_p25 = ref_p25
        self.land_sea_mask = land_sea_mask
        self.expiry_days = expiry_days
        self.min_length = min_length
        self.min_samples = min_samples
        self.radius = neighbor_radius
        self.output_path = output_path
        self.use_dbscan = use_dbscan
        self.eventtype = eventtype
        self.land_only = land_only
        self.ocean_only = ocean_only
        
        # Initialize state
        self.active = []  # Currently tracked events
        self.output_queue = deque()  # Completed events awaiting retrieval
        self.oldest_active_time = None
        self.id = 0
        self.skipToTime = None

        # Create threshold mask based on event type
        if eventtype == 'wet':
            # Precipitation: (precip - ref) / IQR > 0
            # Only calculate for wet days (>= 1mm)
            iqr = ref_p75 - ref_p25
            # Guard against zero IQR (flat climatology pixel) to avoid
            # divide-by-zero warnings from dask; those pixels are excluded.
            safe_iqr = iqr.where(iqr > 0, other=1.0)
            anomaly = (data - ref_data) / safe_iqr
            # Only count genuine wet days (>= 1mm) to avoid noise from trace precip
            self.raw_mask = (anomaly > self.threshold) & (iqr > 0) & (data >= WET_DAY_THRESHOLD)
            # Store the anomaly DataArray so we can record it as event intensity
            self.anomaly = anomaly
            # No persistence filtering for precipitation
            self.enduring_pixels = self.raw_mask
        else:
            # Temperature: existing logic
            if self.over_threshold:
                self.raw_mask = (data > self.threshold) & (data > ref_data)
            else:
                self.raw_mask = (data < self.threshold) & (data < ref_data)
            
            # Filter for persistence: require 3 consecutive time steps
            # two step process using rolling to first find centre of sequences (hits) using .rolling.sum() then
            # assign all elements of a sequence (enduring_pixels) using .rolling.max().
            hits = (
                    self.raw_mask.rolling(valid_time=3, center=True).sum().fillna(0) >= 3
            )
            self.enduring_pixels = (
                hits.rolling(valid_time=3, center=True).max().fillna(0).astype(bool)
            )

        # Exclude last 2 time steps where rolling window is incomplete
        self.times = self.data.valid_time.values[:-2]

        # Resume from previous state if provided
        if last_slice_name:
            if os.path.exists(last_slice_name):
                with open(last_slice_name, "rb") as f:
                    last_slice_data = pickle.load(f)

                    logger.info(f"Resuming from last slice at {last_slice_data['time']}")
                    self.skipToTime = last_slice_data['time']
                    self.active = last_slice_data.get("active_events", [])
                    
                    if self.active:
                        self.oldest_active_time = min(ev.earliest_time() for ev in self.active)
                    else:
                        self.oldest_active_time = None
                    
                    logger.info(f"Resumed {len(self.active)} active events")
        self.last_slice_name = last_slice_name
        self._t_index = 0  # Index of the next time slice to process
        if self.skipToTime:
            while (self._t_index < len(self.times) and 
                   self.times[self._t_index] <= np.datetime64(self.skipToTime)):
                self._t_index += 1
        
        logger.info(f"{self._t_index} is the t index, {self.skipToTime}")
        
    def has_more(self):
        return self._t_index < len(self.times)

    def process_next_slice(self):
        """
        Process a single time slice: detect clusters, update active events, expire old ones.
        
        This is the main processing method called for each time step. It:
        1. Identifies threshold-exceeding points with persistence (temp) or wet days (precip)
        2. Clusters them spatially using distance-based clustering
        3. Matches clusters to existing events or creates new events
        4. Expires events that haven't been updated recently
        5. Saves state for potential resumption
        """
        # Handle resumption: skip slices until we reach the resumption point
        time = self.times[self._t_index]
        self._t_index += 1
        logger.info(f"Processing slice at {time}")

        # Load data for this time slice
        data_slice = self.data.sel(valid_time=time).load()
        t = np.searchsorted(self.times, np.datetime64(time))

        # Apply persistence filter to raw mask (or just raw mask for precip)
        raw_mask_slice = self.raw_mask.isel(valid_time=t).values
        enduring_slice = np.where(self.enduring_pixels[t], raw_mask_slice, False)

        # Get indices of threshold-exceeding points
        hot_indices = np.argwhere(enduring_slice)  # shape (N, 2): (i_lat, i_lon)

        # Extract coordinate arrays
        lat_vals = data_slice.latitude.values
        lon_vals = data_slice.longitude.values

        # Compute sparse distance matrix for spatial clustering
        D, metadata = self.get_distance_matrix(
            hot_indices, lat_vals, lon_vals, radius_km=self.radius
        )

        # Perform spatial clustering
        if not self.use_dbscan:
            labels = walk_scan(D, eps=self.radius, min_samples=self.min_samples)
        elif D.getnnz() > 0:
            db = DBSCAN(
                eps=self.radius,
                min_samples=self.min_samples,
                metric="precomputed",
            )
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="Precomputed sparse input was not sorted",
                    category=UserWarning,
                )
                labels = db.fit_predict(D.tocsr())
        else:
            labels = []

        # Group points by cluster label
        blobs = []
        for label in set(labels):
            if label == -1:  # Skip noise points
                continue
            points = [m for i, m in enumerate(metadata) if labels[i] == label]
            blobs.append(points)

        # For wet events use the anomaly (IQR-normalised) as intensity;
        # for temperature events use the raw data value.
        # Either way, load into memory now so per-pixel lookups below don't
        # each trigger a separate dask graph evaluation.
        if self.eventtype == 'wet':
            value_slice = self.anomaly.isel(valid_time=t).load()
        else:
            value_slice = data_slice  # already .load()ed above

        # Pre-extract values for every blob using vectorized numpy indexing.
        # Doing .sel(lat, lon).item() in a Python loop costs O(N log N) per blob
        # (binary search per point); this approach is O(N) after one coordinate
        # lookup to build integer index arrays.
        lat_index = {v: i for i, v in enumerate(value_slice.latitude.values)}
        lon_index = {v: i for i, v in enumerate(value_slice.longitude.values)}
        vs_np = value_slice.values  # 2-D numpy array (lat, lon)

        def blob_values(blob):
            i_lats = np.fromiter((lat_index[lat] for lat, lon in blob), dtype=np.intp, count=len(blob))
            i_lons = np.fromiter((lon_index[lon] for lat, lon in blob), dtype=np.intp, count=len(blob))
            return vs_np[i_lats, i_lons]

        # Match blobs to existing active events
        used_blobs = set()
        for i, blob in enumerate(blobs):
            for ev in self.active:
                if ev.overlaps(blob, time):
                    ev.extend(time, blob, blob_values(blob))
                    used_blobs.add(i)
                    break

        # Create new eventlets for unmatched blobs
        for i, blob in enumerate(blobs):
            if i in used_blobs:
                continue
            new_ev = Eventlet(time, blob, blob_values(blob))
            self.active.append(new_ev)

        # Expire old events
        for ev in list(self.active):  # Copy list to avoid mutation issues
            if ev.is_expired(time, self.expiry_days):
                if ev.is_valid(self.min_length, self.min_samples):
                    self._finalize_cluster(ev)
                self.active.remove(ev)

        # Sort active events by size (largest first) for better matching
        self.active.sort(key=lambda ev: len(ev.values[-1]), reverse=True)
        logger.info(f"Slice processed, {len(self.active)} active events")

        # Update oldest active time
        self.oldest_active_time = min(
            (ev.earliest_time() for ev in self.active), default=None
        )

        if self.last_slice_name is not None:
            # Save state for resumption
            last_slice = {
                "time": time,
                "active_events": self.active,
            }
            with open(self.last_slice_name, "wb") as f:
                pickle.dump(last_slice, f)

    def flush(self):
        """
        Finalize and queue all remaining active events.
        
        Called at the end of processing to ensure no events are lost.
        Moves all active events to the output queue.
        """
        for ev in self.active:
            self.output_queue.append(ev)
        self.active = []

    def yield_completed(self):
        """
        Generator yielding finalized events from the output queue.
        
        Yields:
            Eventlet objects that have been finalized and are ready for output
        """
        while self.output_queue:
            yield self.output_queue.popleft()

    def get_distance_matrix(self, coords, lat_arr, lon_arr, radius_km=500):
        """
        Compute sparse distance matrix for spatial clustering.
        
        Builds a sparse matrix containing only pairwise distances below radius_km.
        Uses grid-based neighbor search for efficiency: only tests points within
        a lat/lon bounding box, then computes exact Haversine distances.
        
        Args:
            coords: Array of grid indices, shape (N, 2) with columns [i_lat, i_lon]
            lat_arr: Latitude values for each grid row
            lon_arr: Longitude values for each grid column
            radius_km: Maximum distance threshold in kilometers
            
        Returns:
            Tuple of (D, metadata) where:
            - D: scipy COO sparse matrix of distances, shape (M, M)
            - metadata: List of (lat, lon) tuples for each unique point
            
        Note:
            Handles longitude wraparound correctly by using modulo arithmetic.
        """
        lon_len = len(lon_arr)

        # Build metadata: unique coordinate mappings
        metadata = []
        metadata_index = {}

        coord_set = set(map(tuple, coords))

        def get_uid(i_lat, i_lon):
            """Generate unique ID for grid cell."""
            return i_lat * lon_len + i_lon

        def ensure_metadata(i_lat, i_lon):
            """Add coordinate to metadata if not already present."""
            uid = get_uid(i_lat, i_lon)
            if uid not in metadata_index:
                metadata_index[uid] = len(metadata)
                metadata.append((float(lat_arr[i_lat]), float(lon_arr[i_lon])))
            return metadata_index[uid]

        # Sparse matrix construction lists
        p1idx = []  # Source point indices
        p2idx = []  # Target point indices
        dists = []  # Distances

        # Compute search radius in grid cells
        res = 0.25  # Grid resolution in degrees
        radius_km_per_deg = 111  # Approximate km per degree
        radius_deg = radius_km / radius_km_per_deg
        delta_coord = 2 * int(np.ceil(radius_deg / res))  # 2x for safety margin
        delta_list = np.arange(-delta_coord, delta_coord + 1, 1)

        # For each point, check neighbors within bounding box
        for i_lat, i_lon in coords:
            i_idx = ensure_metadata(i_lat, i_lon)
            
            for dlat in delta_list:
                for dlon in delta_list:
                    if dlat == 0 and dlon == 0:
                        continue  # Skip self
                    
                    j_lat = i_lat + dlat
                    j_lon = (i_lon + dlon) % lon_len  # Handle longitude wraparound

                    # Check if neighbor exists in our coordinate set
                    if (j_lat, j_lon) in coord_set:
                        # Compute exact Haversine distance
                        d_km = haversine_fast(
                            (lat_arr[i_lat], lon_arr[i_lon]),
                            (lat_arr[j_lat], lon_arr[j_lon])
                        )
                        
                        # Only store if within radius
                        if d_km <= radius_km:
                            j_idx = ensure_metadata(j_lat, j_lon)
                            p1idx.append(i_idx)
                            p2idx.append(j_idx)
                            dists.append(d_km)

        # Build symmetric sparse matrix
        D = coo_matrix((dists, (p1idx, p2idx)), shape=(len(metadata), len(metadata)))
        D = D + D.T  # Make symmetric
        
        return D, metadata

    def _finalize_cluster(self, ev):
        """
        Finalize a completed event and write output files.
        
        Generates comprehensive metadata including:
        - Temporal information (times, duration)
        - Spatial information (geometries, centroids, bounding box)
        - Statistical summaries (max/mean/min values)
        - Per-pixel maximum values
        - Land/ocean classification
        
        Writes two output files:
        1. Catalogue entry (JSONL): Compact summary for quick searches
        2. Full event file (JSON): Complete details including all time slices
        
        Args:
            ev: Eventlet object to finalize
        """
        # Apply land/ocean filtering if requested
        if self.land_only:
            ev.remove_ocean(self.land_sea_mask)
            if not ev.is_valid(self.min_length, self.min_samples):
                logger.info(f"Discarding event at {ev.times[0]} for being too small over land")
                return
        elif self.ocean_only:
            ev.remove_land(self.land_sea_mask)
            if not ev.is_valid(self.min_length, self.min_samples):
                logger.info(f"Discarding event at {ev.times[0]} for being too small over ocean")
                return

        all_times = sorted([pd.Timestamp(t) for t in ev.times])
        logger.info(f"Finalising extreme event from {all_times[0]} to {all_times[-1]}")
        # Collect coordinates and compute centroids
        all_coords = []
        centroids = []
        for i, region in enumerate(ev.slices):
            latlons = [(float(lat), float(lon)) for lat, lon in region]
            all_coords.extend(latlons)
            centroids.append(ev.centroid(i))

        # Compute bounding box
        lats, lons = zip(*all_coords)
        bbox = [float(min(lats)), float(min(lons)), float(max(lats)), float(max(lons))]

        # Generate stable event ID
        event_id = get_id(self.eventtype, ev)

        # Compute statistics across time slices
        # NOTE: compute raw numpy aggregates BEFORE to_serializable, which converts
        # np.nan → None. Passing a list of Nones to np.nanmax raises TypeError.
        _raw_max_values = [
            np.nanmax(ev.values[i]) if len(ev.values[i]) > 0 else np.nan
            for i in range(len(ev.slices))
        ]
        max_values = to_serializable(_raw_max_values)
        max_value = to_serializable(np.nanmax(_raw_max_values)) if _raw_max_values else np.nan

        _raw_mean_values = [
            np.nanmean(ev.values[i]) if len(ev.values[i]) > 0 else np.nan
            for i in range(len(ev.slices))
        ]
        mean_values = to_serializable(_raw_mean_values)
        mean_value = (
            to_serializable(np.mean(np.concatenate(ev.values)))
            if _raw_mean_values else np.nan
        )

        _raw_min_values = [
            np.nanmin(ev.values[i]) if len(ev.values[i]) > 0 else np.nan
            for i in range(len(ev.slices))
        ]
        min_values = to_serializable(_raw_min_values)
        min_value = to_serializable(np.nanmin(_raw_min_values)) if _raw_min_values else np.nan

        # Determine if event is ocean-only
        ocean_only = False
        if self.land_sea_mask is not None:
            all_ocean = True
            lat_asc = np.all(np.diff(self.land_sea_mask.latitude) > 0)
            lats = self.land_sea_mask.latitude.values
            if not lat_asc:
                lats = lats[::-1]

            # Check each time slice for land points
            for i in range(len(ev.slices)):
                if ev.hull(i) is not None:
                    coords = np.array(ev.slices[i])
                    
                    # Map coordinates to mask indices
                    lat_indices = np.searchsorted(lats, coords[:, 0])
                    lat_indices = np.clip(
                        lat_indices, 0, self.land_sea_mask.latitude.size - 1
                    )
                    if not lat_asc:
                        lat_indices = self.land_sea_mask.latitude.size - 1 - lat_indices

                    lon_indices = np.searchsorted(
                        self.land_sea_mask.longitude, coords[:, 1]
                    )
                    lon_indices = np.clip(
                        lon_indices, 0, self.land_sea_mask.longitude.size - 1
                    )

                    # Check mask values
                    mask_values = self.land_sea_mask.values[0, lat_indices, lon_indices]
                    if not np.all(mask_values == 0):
                        all_ocean = False
                        break
            
            ocean_only = all_ocean

        if ocean_only:
            logger.info(f"Event {event_id} is ocean-only, with centroid {centroids[0]}")

        # Compute per-pixel maximum values across all time slices
        all_coords = np.vstack([np.asarray(t_slice) for t_slice in ev.slices])
        all_values = np.hstack([np.asarray(vals).ravel() for vals in ev.values])

        if all_coords.shape[0] != all_values.shape[0]:
            raise ValueError(
                f"Coordinate/value mismatch: {all_coords.shape[0]} coords "
                f"vs {all_values.shape[0]} values"
            )

        # Find unique coordinates and compute max value at each pixel
        coords_view = all_coords.view(
            [("", all_coords.dtype)] * all_coords.shape[1]
        ).ravel()
        unique_coords, inverse_idx = np.unique(coords_view, return_inverse=True)

        pixel_max_values = np.full(len(unique_coords), -np.inf, dtype=all_values.dtype)
        np.maximum.at(pixel_max_values, inverse_idx, all_values)

        # Convert back to normal array
        unique_coords = unique_coords.view(all_coords.dtype).reshape(
            -1, all_coords.shape[1]
        )
        pixel_set = unique_coords.tolist()
        # Loop over unique coords to calculate total area, weighted by cosine of latitude
        def calculate_area(pixel_set):
            total_area = 0.0
            for lat, lon in pixel_set:
                # Approximate area of 0.25 x 0.25 degree grid cell at given latitude
                lat_rad = np.radians(lat)
                cell_area = (
                    (111.32 * 0.25) * (111.32 * 0.25 * np.cos(lat_rad))
                )  # in km^2
                total_area += cell_area
            return total_area
        total_area = calculate_area(pixel_set)
        areas = [calculate_area(slice.tolist()) for slice in ev.slices]

        # Compute overall event geometry
        total_region_shape = safe_alphashape(unique_coords, alpha=1.0)

        # Build full event dictionary
        full_event = {
            "id": event_id,
            "event_type": self.eventtype,
            "times": [format_time(t) for t in all_times],
            "regions": [get_region(ev.hull(i)) for i in range(len(ev.slices))],
            "total_region": get_region(total_region_shape),
            "slices": to_serializable(ev.slices),
            "values": to_serializable(ev.values),
            "centroids": to_serializable(centroids),
            "bbox": to_serializable(bbox),
            "total_area": total_area,
            "areas": to_serializable(areas),
            "max_values": max_values,
            "max_value": max_value,
            "mean_values": mean_values,
            "mean_value": mean_value,
            "min_values": min_values,
            "min_value": min_value,
            "ocean_only": ocean_only,
            "pixel_set": pixel_set,
            "pixel_count": len(pixel_set),
            "pixel_max_values": to_serializable(pixel_max_values),
        }

        def pack_pixel_to_int(lat: float, lon: float) -> int:
            """
            Pack lat/lon into 32-bit integer for compact storage.
            
            Encodes coordinates at 0.25 degree resolution:
            - Latitude in upper 16 bits: [-90, 90] → [0, 720]
            - Longitude in lower 16 bits: [-180, 180] → [0, 1440]
            """
            i_lat = int(np.round(lat * 4))
            
            # Normalize longitude to [-180, 180]
            while lon < -180:
                lon += 360
            while lon > 180:
                lon -= 360
            
            i_lon = int(np.round(lon * 4))
            return (i_lat << 16) | (i_lon & 0xFFFF)

        # Build compact catalogue entry
        catalogue_event = {
            "id": full_event["id"],
            "event_type": self.eventtype,
            "times": full_event["times"],
            "regions": full_event["regions"],
            "total_region": full_event["total_region"],
            "bbox": full_event["bbox"],
            "max_value": full_event["max_value"],
            "mean_value": full_event["mean_value"],
            "min_value": full_event["min_value"],
            "total_area": full_event["total_area"],
            "ocean_only": ocean_only,
            "pixel_set": [pack_pixel_to_int(*coord) for coord in pixel_set],
        }

        # Write outputs
        year = all_times[0].strftime('%Y')
        catalogue_path = f"{self.output_path}/events-{self.eventtype}-{year}.jsonl"
        event_path = f"{self.output_path}/events/event-{event_id}.json"

        with open(catalogue_path, "a") as f:
            f.write(json.dumps(round_floats(catalogue_event)) + "\n")
        
        with open(event_path, "w") as f:
            f.write(json.dumps(round_floats(full_event)) + "\n")


# Configure logging
root_logger = logging.getLogger()
if root_logger.hasHandlers():
    root_logger.handlers.clear()

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

# Parameter set definition
ParamSet = namedtuple(
    "ParamSet",
    ["stat", "perc", "thresh", "nr", "ms", "dbscan", "event_mode"]
)


def get_default_params() -> List[ParamSet]:
    """
    Get default parameter sets for event detection.
    
    Returns:
        List of ParamSet tuples defining detection parameters
        
    Parameter descriptions:
        stat: Statistic type ('min', 'max' for temp, 'tp' for precip)
        perc: Climatological percentile threshold (e.g., '99.0', '95.0')
        thresh: Absolute threshold in Celsius (None for precip)
        nr: Neighbor radius in km for spatial clustering (default: 250)
        ms: Minimum samples for DBSCAN cluster size (default: 30)
        dbscan: Use sklearn DBSCAN if True, custom walk_scan if False
        event_mode: 'hot', 'cold', or 'wet'
    """
    return [
        ParamSet(
            stat="min",
            perc="2.0",
            thresh=0,
            nr=500,
            ms=60,
            dbscan=True,
            event_mode='cold'
        ),
        ParamSet(
            stat="max",
            perc="98.0",
            thresh=28,
            nr=500,
            ms=60,
            dbscan=True,
            event_mode='hot'
        ),
        ParamSet(
            stat="tp",
            perc="95.0",
            thresh=0.0,
            nr=500,
            ms=60,
            dbscan=True,
            event_mode='wet'
        ),
    ]


def process_parameter_set(
    param: ParamSet,
    input_dir: str = "/data",
    output_dir: str = "/output"
) -> bool:
    """
    Process a single parameter set to detect events.
    
    Args:
        param: ParamSet tuple defining detection parameters
        input_dir: Directory containing ERA5 input data
        output_dir: Directory for output event files
        
    Returns:
        True if processing succeeded, False otherwise
    """
    # Prefix every log line from this worker with the event type so parallel
    # output from multiple processes is easy to distinguish.
    for _h in logger.handlers:
        _h.setFormatter(logging.Formatter(
            f'%(asctime)s - {param.event_mode} - %(levelname)s - %(message)s'
        ))

    logger.info(f"Processing {param.event_mode} events with parameters: {param}")
    
    try:
        # Load input data
        logger.info("Loading data...")
        
        if param.event_mode == 'wet':
            # Load precipitation data with IQR percentiles
            data_var, ref_data, ref_p75, ref_p25, land_sea_mask = load_data(
                f"{input_dir}/precip/era5_daily_total_precipitation*.nc",
                f"{input_dir}/climatology/era5_daily_total_precipitation_95.0pc_wetdays_1991-2020.nc",
                ref_path_p75=f"{input_dir}/climatology/era5_daily_total_precipitation_75.0pc_wetdays_1991-2020.nc",
                ref_path_p25=f"{input_dir}/climatology/era5_daily_total_precipitation_25.0pc_wetdays_1991-2020.nc",
                land_sea_mask_path=f"{input_dir}/era5_land_sea_mask.nc",
            )
        else:
            # Load temperature data
            data_var, ref_data, ref_p75, ref_p25, land_sea_mask = load_data(
                f"{input_dir}/t2m/{param.stat}/era5_daily_{param.stat}_temperature*.nc",
                f"{input_dir}/climatology/era5_daily_{param.stat}_temperature_{param.perc}pc_1991-2020.nc",
                land_sea_mask_path=f"{input_dir}/era5_land_sea_mask.nc",
            )
        
        # Generate parameter string for filenames
        param_str = (
            f"{param.stat}-{param.perc}-{param.thresh if param.thresh is not None else 'iqr'}-"
            f"nr{param.nr}-ms{param.ms}-"
            f"{'dbscan' if param.dbscan else 'walk'}-"
            f"{param.event_mode}"
        )
        
        # Set up output directories
        out_path = output_dir
        os.makedirs(out_path, exist_ok=True)
        os.makedirs(f"{out_path}/events", exist_ok=True)
        
        # Initialize event factory
        logger.info("Initializing EventletFactory...")
        factory = EventletFactory(
            data_var,
            ref_data=ref_data,
            ref_p75=ref_p75,
            ref_p25=ref_p25,
            threshold=273.15 + param.thresh if param.event_mode != 'wet' else param.thresh,
            over_threshold=param.event_mode == 'hot',
            land_sea_mask=land_sea_mask,
            neighbor_radius=param.nr,
            min_samples=param.ms,
            output_path=out_path,
            use_dbscan=param.dbscan,
            last_slice_name=f"{out_path}/last_slice-{param_str}.pkl",
            eventtype=param.event_mode,
            land_only=land_sea_mask is not None
        )
        logger.info(f"{out_path}/last_slice-{param_str} ,_ last slice")

        # Process all time slices
        logger.info("Processing time slices...")
        while factory.has_more():
            factory.process_next_slice()

        # Now the factory is up-to-date. There are still events in the pipeline, but
        # these have been persisted to disk for resumption later.
        
        logger.info(f"Successfully completed {param.event_mode} event detection")
        return True
        
    except Exception as e:
        logger.error(f"Failed to process {param.event_mode} events: {e}", exc_info=True)
        return False


def main():
    """
    Main entry point for event detection pipeline.
    
    Processes all configured parameter sets in parallel using
    ProcessPoolExecutor (one process per ParamSet). Environment
    variables can override default paths:
        EVENT_INPUT_DIR: Input data directory (default: /data)
        EVENT_OUTPUT_DIR: Output directory (default: /output)
        EVENT_MAX_WORKERS: Max parallel workers (default: number of param sets)
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed

    logger.info("=" * 60)
    logger.info("ERA5 Extreme Event Detection Pipeline")
    logger.info("=" * 60)
    
    # Get paths from environment or use defaults
    input_dir = os.environ.get("EVENT_INPUT_DIR", "/data")
    output_dir = os.environ.get("EVENT_OUTPUT_DIR", "/output")
    
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    
    # Get parameter sets
    params = get_default_params()
    
    # Cap workers at number of param sets (no point spinning up more)
    max_workers = int(os.environ.get("EVENT_MAX_WORKERS", len(params)))
    logger.info(
        f"Processing {len(params)} parameter set(s) "
        f"with up to {max_workers} parallel worker(s)"
    )
    
    results = {}
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_param = {
            executor.submit(process_parameter_set, param, input_dir, output_dir): param
            for param in params
        }
        for future in as_completed(future_to_param):
            param = future_to_param[future]
            try:
                success = future.result()
            except Exception as e:
                logger.error(
                    f"Parameter set {param.event_mode} raised an exception: {e}",
                    exc_info=True,
                )
                success = False
            results[param.event_mode] = success
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"{param.event_mode.capitalize()} events finished: {status}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Processing Summary")
    logger.info("=" * 60)
    
    for event_type, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        logger.info(f"{event_type.capitalize()} events: {status}")
    
    # Exit with appropriate code
    if all(results.values()):
        logger.info("All parameter sets completed successfully!")
        return 0
    else:
        logger.error("Some parameter sets failed")
        return 1


if __name__ == "__main__":
    exit(main())