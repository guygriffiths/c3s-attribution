#!/usr/bin/env python3

# Standard library imports
import json
import math
import os
import logging, sys
import pickle
import tempfile
from collections import deque, namedtuple
from typing import List, Tuple, Union, Optional

# Third-party imports
import numpy as np
import pandas as pd
import xarray as xr
from scipy.spatial import Delaunay
from shapely.geometry import MultiLineString, MultiPoint, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union

# Local imports (if any)
# from .module import something

# ============================================================================
# Constants
# ============================================================================

# Mean Earth radius in kilometers
R = 6371.0088
WET_DAY_THRESHOLD = 1.0 * 1e-3  # 1mm in meters - minimum precipitation for "wet day"

# Upper bound on how many time steps are read at once. Reads are aligned to the
# source file's compression chunks, but a file chunked over a very long span
# would otherwise pull an unreasonable amount into memory at once: one step of
# ERA5 at 0.25 degrees is 4 MB as float32.
MAX_READ_BLOCK = 73

# ============================================================================
# Grid Cell Keys
# ============================================================================

def pack_cell_keys(coords) -> np.ndarray:
    """
    Pack (lat, lon) coordinates into unique integer grid-cell keys.

    Coordinates are snapped to 0.001 degrees, which is far finer than the
    0.25 degree data grid but coarse enough to be immune to float round-trips.
    This makes "do these two points occupy the same cell?" an integer equality
    test, so sets of cells can be intersected directly.

    Args:
        coords: Array-like of shape (N, 2) with columns [lat, lon]

    Returns:
        Array of int64 keys, shape (N,)
    """
    arr = np.asarray(coords, dtype=np.float64).reshape(-1, 2)
    lat = np.rint(arr[:, 0] * 1000.0).astype(np.int64) + 90_000
    lon = np.rint(arr[:, 1] * 1000.0).astype(np.int64) + 180_000
    return lat * 1_000_000 + lon


# ============================================================================
# Distance and Geometry Calculations
# ============================================================================

def haversine_row_offsets(lat1_deg: float, lat2_deg: float, dlon_deg: np.ndarray) -> np.ndarray:
    """
    Great-circle distances between two fixed latitudes over an array of
    longitude offsets.

    For a fixed pair of latitudes the Haversine distance depends only on the
    longitude difference, and it increases monotonically with |dlon| over the
    half circle. That lets a whole row pair be handled with one small table
    instead of a distance computation per point pair.

    Args:
        lat1_deg: Latitude of the first row in degrees
        lat2_deg: Latitude of the second row in degrees
        dlon_deg: Array of longitude offsets in degrees

    Returns:
        Array of distances in kilometers, same shape as dlon_deg
    """
    lat1 = math.radians(lat1_deg)
    lat2 = math.radians(lat2_deg)
    dlat = lat2 - lat1
    dlon = np.radians(dlon_deg)

    a = (math.sin(dlat * 0.5) ** 2 +
         math.cos(lat1) * math.cos(lat2) * np.sin(dlon * 0.5) ** 2)

    return R * (2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))


def alpha_shape(
    points: np.ndarray,
    alpha: float
) -> Optional[Union[Polygon, MultiPolygon]]:
    """
    Compute the alpha shape of a set of points.

    Triangulate the points, discard every triangle whose circumcircle is
    larger than the alpha radius, and return the union of what is left.

    This is what alphashape.alphashape does, but that walks the triangles in
    Python, solving a four by four system and doing set arithmetic over
    itertools.combinations for each one. An event footprint runs to tens of
    thousands of triangles, so the loop dominates. Doing the same arithmetic
    in numpy over all the triangles at once gives the same shape about eight
    times faster.

    Args:
        points: Array of coordinates, shape (N, 2)
        alpha: Triangles with a circumradius above 1 / alpha are discarded,
            so a larger alpha gives a tighter fit

    Returns:
        Shapely Polygon/MultiPolygon, or None if no triangle survives

    Raises:
        scipy.spatial.QhullError: if the points have no triangulation, which
            happens when there are fewer than three of them or they are all
            collinear
    """
    points = np.asarray(points, dtype=np.float64)
    simplices = Delaunay(points).simplices
    corners = points[simplices]                       # (M, 3, 2)
    count = len(simplices)

    # The circumcentre in barycentric coordinates is the solution of a system
    # built from the Gram matrix of the corners, bordered to make the weights
    # sum to one.
    system = np.empty((count, 4, 4))
    system[:, :3, :3] = 2.0 * (corners @ corners.transpose(0, 2, 1))
    system[:, :3, 3] = 1.0
    system[:, 3, :3] = 1.0
    system[:, 3, 3] = 0.0
    target = np.empty((count, 4, 1))
    target[:, :3, 0] = np.sum(corners * corners, axis=2)
    target[:, 3, 0] = 1.0

    # A singular system means a degenerate triangle, which has no circumcircle
    # and has to be dropped before solving rather than after: one of them would
    # otherwise fail the whole batch.
    circumradius = np.full(count, np.inf)
    solvable = np.abs(np.linalg.det(system)) > 1e-12
    if solvable.any():
        kept_corners = corners[solvable]
        weights = np.linalg.solve(system[solvable], target[solvable])[:, :3, 0]
        centres = np.einsum("mi,mij->mj", weights, kept_corners)
        circumradius[solvable] = np.linalg.norm(
            kept_corners[:, 0] - centres, axis=1
        )

    survivors = simplices[circumradius < 1.0 / alpha]
    if len(survivors) == 0:
        return None

    # An edge is on the perimeter when exactly one surviving triangle uses it.
    edges = np.sort(np.concatenate([
        survivors[:, [0, 1]], survivors[:, [1, 2]], survivors[:, [2, 0]]
    ]), axis=1)
    unique_edges, use_count = np.unique(edges, axis=0, return_counts=True)
    perimeter = unique_edges[use_count == 1]
    if len(perimeter) == 0:
        return None

    return unary_union(list(polygonize(
        MultiLineString(list(points[perimeter]))
    )))


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
            shape = alpha_shape(points, alpha)
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


def write_atomic(path: str, text: str) -> None:
    """
    Write text to path so that readers only ever see a complete file.

    The active-event files are rewritten while a client may be fetching them,
    so writing in place would expose truncated JSON. Write to a temporary file
    in the same directory and rename over the target, which is atomic within a
    filesystem.

    Args:
        path: Destination file path
        text: Complete contents to write
    """
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".part")
    try:
        # Explicitly set permissions to 644 before writing
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


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

        Memoised on the identity of the slice's coordinate array, so any
        operation that rebinds ``self.slices[n]`` invalidates the entry.

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

        cache = getattr(self, "_hull_cache", None)
        if cache is None:
            cache = self._hull_cache = {}

        entry = cache.get(n)
        if entry is not None and entry[0] is target_slice and entry[1] == alpha:
            return entry[2]

        shape = safe_alphashape(target_slice, alpha)
        cache[n] = (target_slice, alpha, shape)
        return shape

    def region(self, n, alpha=1.0):
        """
        Return the serialisable region for time slice ``n``, caching the result
        until that slice's coordinate array is replaced.

        Equivalent to ``get_region(self.hull(n, alpha))``, but memoised. An
        active event is re-serialised on every time step, so without this the
        alpha shape for every slice would be recomputed every step, making the
        cost of publishing an event quadratic in its duration.

        The cache is keyed on array identity, so any operation that rebinds
        ``self.slices[n]`` (extend, merge, land/ocean filtering) transparently
        invalidates it.

        Args:
            n: Index of the time slice
            alpha: Alpha parameter controlling hull tightness (default 1.0)

        Returns:
            List of polygons, each a list of [lon, lat] pairs
        """
        if not self.slices:
            return get_region(None)

        target = self.slices[n] if n < len(self.slices) else self.slices[-1]

        cache = getattr(self, "_region_cache", None)
        if cache is None:
            cache = self._region_cache = {}

        entry = cache.get(n)
        if entry is not None and entry[0] is target and entry[1] == alpha:
            return entry[2]

        region = get_region(self.hull(n, alpha))
        cache[n] = (target, alpha, region)
        return region

    def overlaps(self, coords, time):
        """
        Check whether any of the provided coordinates coincide with the
        eventlet's relevant slice.

        All coordinates originate from the same regular grid, so "overlap"
        is exact coincidence of grid cells. This is evaluated as a set
        intersection over packed integer cell keys, which is O(N + M) rather
        than the O(N * M) pairwise comparison it replaces.

        Args:
            coords: Array of (lat, lon) coordinates to test, shape (N, 2)
            time: Timestamp of the slice being matched

        Returns:
            True if any test point occupies the same grid cell as a point in
            the eventlet's relevant slice
        """
        idx = (self.times.index(time) - 1) if (time in self.times) and (self.times.index(time) > 0) else -1
        current_keys = self._slice_keys(idx)
        if not current_keys:
            return False

        return not current_keys.isdisjoint(pack_cell_keys(coords).tolist())

    def _slice_keys(self, idx):
        """
        Return the set of packed grid-cell keys for slice ``idx``, caching the
        result until that slice's coordinate array is replaced.

        The cache is keyed on array identity, so any operation that rebinds
        ``self.slices[idx]`` (extend, merge, land/ocean filtering, re-sorting)
        transparently invalidates it.
        """
        target = self.slices[idx]
        cache = getattr(self, "_keys_cache", None)
        if cache is None:
            cache = self._keys_cache = {}

        entry = cache.get(idx)
        if entry is not None and entry[0] is target:
            return entry[1]

        keys = set(pack_cell_keys(target).tolist())
        cache[idx] = (target, keys)
        return keys

    def __getstate__(self):
        """Exclude the derived caches from pickled state."""
        state = self.__dict__.copy()
        for cache in ("_keys_cache", "_hull_cache", "_region_cache",
                      "_footprint_cache", "_payload_cache"):
            state.pop(cache, None)
        return state

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
            if len(self.slices[i]) > 0:
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
            if len(self.slices[i]) > 0:
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
            min_samples: Minimum cluster size for DBSCAN
            output_path: Directory path for output files
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
        self.eventtype = eventtype
        self.land_only = land_only
        self.ocean_only = ocean_only
        
        # Initialize state
        self.active = []  # Currently tracked events
        self.output_queue = deque()  # Completed events awaiting retrieval
        self.oldest_active_time = None
        self.id = 0
        self.skipToTime = None
        self._mask_cache = {}  # Raw mask slices, keyed by time index
        self._width_cache = {}  # Longitude reach, keyed by pair of grid rows

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
        else:
            # Temperature: existing logic
            if self.over_threshold:
                self.raw_mask = (data > self.threshold) & (data > ref_data)
            else:
                self.raw_mask = (data < self.threshold) & (data < ref_data)

        # Persistence is applied per slice in _enduring_at, from cached mask
        # slices, rather than as a rolling expression over the whole record

        # Exclude last 2 time steps where rolling window is incomplete
        self._n_times = self.raw_mask.sizes["valid_time"]
        self.times = self.data.valid_time.values[:-2]

        # Coordinates are the same for every slice, so resolve them once
        self._lat_vals = self.data.latitude.values
        self._lon_vals = self.data.longitude.values
        self._lat_index = {v: i for i, v in enumerate(self._lat_vals)}
        self._lon_index = {v: i for i, v in enumerate(self._lon_vals)}

        # Reads are served a whole storage chunk at a time; see _read_span
        self._read_block = self._storage_time_chunk()
        self._value_block = None  # (start, stop, 3-D array) for the values

        # Resume from previous state if provided
        if last_slice_name:
            if os.path.exists(last_slice_name):
                with open(last_slice_name, "rb") as f:
                    import sys
                    if '__mp_main__' in sys.modules:
                        sys.modules['__mp_main__'].Eventlet = Eventlet  # Inject class into worker namespace
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

    def reset_catalogues(self):
        """
        Discard the year catalogues belonging to this event type.

        Finished events are appended to their year's catalogue as they expire,
        which is what makes an interrupted run cheap to continue: the resume
        state says which slice to carry on from and everything written before
        it still stands. A run that starts with no resume state is a different
        matter, because it replays the record from the beginning and would
        append every event a second time.

        Checking each event against what is already on disk would mean holding
        every id in memory and paying for the check on every write, to guard
        against something that only happens when the resume state is missing.
        Clearing up front costs one pass over a handful of files and nothing
        at all thereafter.

        Only this event type's files are touched, so the three processes
        running in parallel cannot interfere with each other. The active set
        is left alone, since it is rewritten in full at the end of the run.
        """
        prefix = f"events-{self.eventtype}-"
        for name in os.listdir(self.output_path):
            if not name.startswith(prefix) or not name.endswith(".jsonl"):
                continue
            if not name[len(prefix):-len(".jsonl")].isdigit():
                continue  # the active set, not a year
            logger.info(f"Discarding {name}: reprocessing from the start")
            os.remove(os.path.join(self.output_path, name))

    def _storage_time_chunk(self):
        """
        Number of time steps in one on-disk chunk of the source data.

        ERA5 files as delivered are compressed with chunks spanning many days
        at once, so extracting a single day forces the whole chunk to be
        decompressed. Reads are aligned to that boundary to pay the cost once.

        Returns:
            Chunk length along valid_time, or MAX_READ_BLOCK if it cannot be
            determined or is implausibly large
        """
        chunks = self.data.encoding.get("chunksizes")
        dims = self.data.dims
        if chunks and "valid_time" in dims:
            length = chunks[dims.index("valid_time")]
            if 1 <= length <= MAX_READ_BLOCK:
                return int(length)
        return MAX_READ_BLOCK

    def _read_span(self, k):
        """
        Chunk-aligned range of time indices to read when index k is wanted.

        Args:
            k: Index along the valid_time dimension

        Returns:
            Tuple of (start, stop) covering k, clipped to the record
        """
        block = self._read_block
        start = (k // block) * block
        return start, min(start + block, self._n_times)

    def _raw_mask_at(self, k):
        """
        Raw threshold mask for one time index, held between slices.

        On a miss the whole surrounding storage chunk is decompressed anyway,
        so the entire span is masked and cached in one pass rather than one
        index at a time. Consecutive slices need overlapping windows of the raw
        mask, and process_next_slice only evicts indices below t - 1, so the
        rest of the span survives to be used by later steps.

        Args:
            k: Index along the valid_time dimension

        Returns:
            2-D boolean array (latitude, longitude)
        """
        cached = self._mask_cache.get(k)
        if cached is None:
            start, stop = self._read_span(k)
            block = self.raw_mask.isel(valid_time=slice(start, stop)).values
            for offset in range(stop - start):
                self._mask_cache.setdefault(start + offset, block[offset])
            cached = self._mask_cache[k]
        return cached

    def _values_at(self, t):
        """
        Intensity values for one time index, read a storage chunk at a time.

        The anomaly for wet events, the raw data otherwise. Only the current
        step's values are ever needed, so a single block is held rather than a
        cache keyed by index.

        Args:
            t: Index along the valid_time dimension

        Returns:
            2-D array (latitude, longitude)
        """
        if self._value_block is not None:
            start, stop, block = self._value_block
            if start <= t < stop:
                return block[t - start]

        start, stop = self._read_span(t)
        source = self.anomaly if self.eventtype == 'wet' else self.data
        block = source.isel(valid_time=slice(start, stop)).values
        self._value_block = (start, stop, block)
        return block[t - start]

    def _hits_at(self, k):
        """
        True where k is the middle of three consecutive exceeding steps.

        Args:
            k: Index along the valid_time dimension

        Returns:
            2-D boolean array, or None where the window runs off either end of
            the record and the result is empty by definition
        """
        if k <= 0 or k >= self._n_times - 1:
            return None
        return (self._raw_mask_at(k - 1)
                & self._raw_mask_at(k)
                & self._raw_mask_at(k + 1))

    def _enduring_at(self, t, raw_mask_slice):
        """
        Apply the persistence filter to one time index.

        Equivalent to indexing the rolling expression built in __init__, but
        evaluated from cached mask slices so the shared steps between
        neighbouring slices are only read once. A pixel survives if it exceeds
        the threshold now and belongs to a run of three consecutive exceeding
        steps starting at t-2, t-1 or t.

        Args:
            t: Index along the valid_time dimension
            raw_mask_slice: Raw threshold mask at t

        Returns:
            2-D boolean array (latitude, longitude)
        """
        if self.eventtype == 'wet':
            return raw_mask_slice  # No persistence requirement for precipitation

        # Both rolling passes are centred and 3 wide, so the ends of the record
        # are incomplete and fill as empty rather than wrapping or shrinking
        if t <= 0 or t >= self._n_times - 1:
            return np.zeros_like(raw_mask_slice)

        enduring = None
        for k in (t - 1, t, t + 1):
            hits = self._hits_at(k)
            if hits is None:
                continue
            enduring = hits if enduring is None else (enduring | hits)

        if enduring is None:
            return np.zeros_like(raw_mask_slice)
        return enduring & raw_mask_slice

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
        t = np.searchsorted(self.times, np.datetime64(time))

        # Apply persistence filter to raw mask (or just raw mask for precip)
        raw_mask_slice = self._raw_mask_at(t)
        enduring_slice = self._enduring_at(t, raw_mask_slice)

        # The next slice reaches back one step further than this one, so
        # anything older can go
        for stale in [k for k in self._mask_cache if k < t - 1]:
            del self._mask_cache[stale]

        # Get indices of threshold-exceeding points
        hot_indices = np.argwhere(enduring_slice)  # shape (N, 2): (i_lat, i_lon)

        # Extract coordinate arrays
        lat_vals = self._lat_vals
        lon_vals = self._lon_vals

        # Cluster the points spatially
        labels = self.cluster_points(
            hot_indices, self.radius, self.min_samples
        )
        metadata = [
            (float(lat_vals[i_lat]), float(lon_vals[i_lon]))
            for i_lat, i_lon in hot_indices
        ]

        # Group points by cluster label.
        # Sorting once is O(n log n); testing every point against every label
        # would be O(n_labels * n_points).
        labels = np.asarray(labels)
        blobs = []
        if labels.size:
            order = np.argsort(labels, kind="stable")
            ordered_labels = labels[order]
            starts = np.flatnonzero(
                np.concatenate(([True], ordered_labels[1:] != ordered_labels[:-1]))
            )
            ends = np.concatenate((starts[1:], [len(ordered_labels)]))
            for start, end in zip(starts, ends):
                if ordered_labels[start] == -1:  # Skip noise points
                    continue
                blobs.append([metadata[i] for i in order[start:end]])

        # For wet events use the anomaly (IQR-normalised) as intensity;
        # for temperature events use the raw data value.
        vs_np = self._values_at(t)  # 2-D numpy array (lat, lon)

        # Pre-extract values for every blob using vectorized numpy indexing.
        # Doing .sel(lat, lon).item() in a Python loop costs O(N log N) per blob
        # (binary search per point); this approach is O(N) after one coordinate
        # lookup to build integer index arrays.
        lat_index = self._lat_index
        lon_index = self._lon_index

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

        # Republishing the active set only matters to a reader watching the
        # live output, and it costs more the larger and older the events in
        # flight are: every step re-serialises every pixel every active event
        # has ever covered. An operational update processes the one slice that
        # has just arrived and stops, so it still publishes. A reprocess of the
        # whole record would otherwise rewrite the same growing events once per
        # day of data, for output nobody reads until the run ends. Publishing
        # on the final slice alone leaves exactly the same files behind.
        if not self.has_more():
            self._publish_active()

    def _publish_active(self):
        """
        Republish the set of events that are still in progress.

        Events are only written to the year catalogue once they expire, so
        without this the most recent events — the ones a reader is most likely
        to care about — are invisible until they are over. This writes the
        current active set in the same shape as the finished output, flagged
        with "provisional": true:

        - ``events-{type}-active.jsonl``, alongside the per-year catalogues
        - ``events-current/event-{id}.json``, alongside the finished events

        Both are rebuilt from scratch every time this runs, so the catalogue
        cannot go stale. The per-event files can, because an event's id is
        derived from its most extreme pixel and that pixel can move as the
        event grows: the same event may be published under a different name
        tomorrow, orphaning today's file. So the directory is reconciled
        against the live set on every call rather than cleaned periodically.

        Note that this is called at the end of a run rather than after every
        slice; see process_next_slice for why.

        Event types run in separate processes and share events-current/, so
        reconciliation only ever considers this process's own event type. Ids
        begin with the type, which makes that a simple prefix test.

        Note that land/ocean filtering is not applied here. It mutates the
        eventlet and so can only run once the event is complete; a provisional
        event may therefore include points that the finished one will not.
        """
        active_dir = f"{self.output_path}/events-current"
        os.makedirs(active_dir, exist_ok=True)

        live = []
        for ev in self.active:
            full_event, catalogue_event = self._build_event(ev, provisional=True)
            live.append(catalogue_event)
            write_atomic(
                f"{active_dir}/event-{full_event['id']}.json",
                json.dumps(round_floats(full_event)) + "\n",
            )

        write_atomic(
            f"{self.output_path}/events-{self.eventtype}-active.jsonl",
            "".join(json.dumps(round_floats(e)) + "\n" for e in live),
        )

        # Drop per-event files this process wrote for ids that are no longer live
        live_ids = {e["id"] for e in live}
        prefix = f"event-{self.eventtype}"
        for name in os.listdir(active_dir):
            if not name.startswith(prefix) or not name.endswith(".json"):
                continue
            if name[len("event-"):-len(".json")] not in live_ids:
                os.remove(os.path.join(active_dir, name))

    def flush(self):
        """
        Finalize and queue all remaining active events.
        
        Called at the end of processing to ensure no events are lost.
        Moves all active events to the output queue.
        """
        for ev in self.active:
            self.output_queue.append(ev)
        self.active = []
        self._publish_active()

    def yield_completed(self):
        """
        Generator yielding finalized events from the output queue.
        
        Yields:
            Eventlet objects that have been finalized and are ready for output
        """
        while self.output_queue:
            yield self.output_queue.popleft()

    def _column_width(self, i_lat1, i_lat2, radius_km):
        """
        Widest longitude offset, in grid columns, still within radius_km for a
        given pair of latitude rows.

        For a fixed pair of latitudes the great-circle distance depends only on
        the longitude difference, and grows with it over the half circle, so a
        single offset separates the neighbours from everything else. Columns
        converge towards the poles, so this has to be derived per row pair: a
        fixed offset would reach steadily less far east-west the further north
        you go.

        The rows are the same at every time step, so answers are kept for the
        life of the factory.

        Args:
            i_lat1: Grid row index of the first row
            i_lat2: Grid row index of the second row
            radius_km: Neighbourhood radius in kilometres

        Returns:
            Largest column offset within the radius, or -1 if the two rows are
            already further apart than the radius on their own
        """
        key = (int(i_lat1), int(i_lat2))
        cached = self._width_cache.get(key)
        if cached is not None:
            return cached

        res = 0.25  # Grid resolution in degrees
        max_width = (len(self._lon_vals) - 1) // 2
        lat1 = float(self._lat_vals[i_lat1])
        lat2 = float(self._lat_vals[i_lat2])

        # Invert the Haversine formula for the longitude offset that lands
        # exactly on the radius, given this pair of latitudes.
        target = (math.sin(0.5 * radius_km / R) ** 2 -
                  math.sin(0.5 * math.radians(lat2 - lat1)) ** 2)
        if target < 0:
            width = -1
        else:
            denom = math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
            if denom <= 0 or target >= denom:
                # Beyond half the globe the window would wrap onto itself and
                # the distance would stop growing with the offset.
                width = max_width
            else:
                width = min(max_width, int(math.degrees(
                    2 * math.asin(math.sqrt(target / denom))
                ) / res) + 1)  # one cell of slack, trimmed exactly below
            table = haversine_row_offsets(
                lat1, lat2, np.arange(width + 1, dtype=np.float64) * res
            )
            width = int(np.searchsorted(table, radius_km, side="right")) - 1

        self._width_cache[key] = width
        return width

    def cluster_points(self, coords, radius_km, min_samples):
        """
        Group grid points into clusters, exactly as DBSCAN would.

        DBSCAN needs two things: which points have at least min_samples
        neighbours within the radius, and how those points connect up. Asking
        it for both through a precomputed distance matrix means materialising
        every pair, and near the poles, where the columns converge, a single
        point can have thousands of neighbours. Most of that work is spent
        proving that the middle of a solid blob is solidly in the middle.

        Both questions can be answered from the grid instead. For a pair of
        latitude rows the neighbours of a point form one contiguous run of
        columns (see _column_width), so counting them is a pair of binary
        searches rather than a distance per candidate. Connectivity is then
        resolved between whole runs of adjacent core columns rather than
        between points, and there are far fewer runs than points.

        The result is the same labelling DBSCAN produces, down to which
        cluster a border point ends up in: clusters are numbered by their
        lowest-numbered core point, which is the order sklearn expands them
        in, and a border point goes to the lowest-numbered cluster that
        reaches it, which is the one that would have claimed it first.

        Args:
            coords: Array of grid indices, shape (N, 2) with columns
                [i_lat, i_lon], in row-major order and free of duplicates,
                which is what np.argwhere produces
            radius_km: Neighbourhood radius in kilometres
            min_samples: Neighbours a point needs to be a core point

        Returns:
            Array of cluster labels, shape (N,), with -1 for noise
        """
        coords = np.asarray(coords, dtype=np.int64).reshape(-1, 2)
        n_points = len(coords)
        labels = np.full(n_points, -1, dtype=np.int64)
        if n_points == 0:
            return labels

        i_lats = coords[:, 0]
        i_lons = coords[:, 1]
        lon_len = len(self._lon_vals)

        # Rows are evenly spaced, so the latitude reach is exact
        dlat_max = int(np.ceil(np.degrees(radius_km / R) / 0.25))

        # Split the points into contiguous latitude rows
        row_starts = np.flatnonzero(
            np.concatenate(([True], i_lats[1:] != i_lats[:-1]))
        )
        row_ends = np.concatenate((row_starts[1:], [n_points]))
        row_ids = i_lats[row_starts]
        row_lookup = {int(r): k for k, r in enumerate(row_ids)}

        # --- Which points are core points -------------------------------
        # Only the size of each neighbour window is needed, not its contents,
        # so no pair is ever built.
        counts = np.zeros(n_points, dtype=np.int64)
        for k_src, row_id in enumerate(row_ids):
            src_from, src_to = row_starts[k_src], row_ends[k_src]
            src_lon = i_lons[src_from:src_to]
            for dlat in range(-dlat_max, dlat_max + 1):
                k_dst = row_lookup.get(int(row_id) + dlat)
                if k_dst is None:
                    continue
                width = self._column_width(row_id, row_id + dlat, radius_km)
                if width < 0:
                    continue

                # Repeat the target row either side so that the window is a
                # plain interval on a sorted array despite the wraparound
                dst_lon = i_lons[row_starts[k_dst]:row_ends[k_dst]]
                extended = np.concatenate(
                    (dst_lon - lon_len, dst_lon, dst_lon + lon_len)
                )
                counts[src_from:src_to] += (
                    np.searchsorted(extended, src_lon + width, side="right")
                    - np.searchsorted(extended, src_lon - width, side="left")
                )

        # A point falls inside its own window, and DBSCAN counts it as one of
        # its own neighbours, so the totals are already on the right footing
        is_core = counts >= min_samples

        # --- Runs of adjacent core columns ------------------------------
        # A run is a maximal stretch of consecutive core columns in one row.
        # Every column in it is a core point, so a run is also a contiguous
        # block of the point list.
        run_row, run_lo, run_hi, run_first, run_len = [], [], [], [], []
        for k, row_id in enumerate(row_ids):
            row_from, row_to = row_starts[k], row_ends[k]
            in_row = np.flatnonzero(is_core[row_from:row_to])
            if len(in_row) == 0:
                continue
            cols = i_lons[row_from:row_to][in_row]

            # Consecutive columns cannot have anything between them, so column
            # continuity alone delimits the runs
            breaks = np.flatnonzero(
                np.concatenate(([True], cols[1:] != cols[:-1] + 1))
            )
            for start, end in zip(breaks, np.concatenate(
                    (breaks[1:], [len(cols)]))):
                run_row.append(int(row_id))
                run_lo.append(int(cols[start]))
                run_hi.append(int(cols[end - 1]))
                run_first.append(int(row_from + in_row[start]))
                run_len.append(int(end - start))

        n_runs = len(run_row)
        if n_runs == 0:
            return labels  # nothing dense enough to seed a cluster

        # --- Connect the runs -------------------------------------------
        parent = list(range(n_runs))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            root_x, root_y = find(x), find(y)
            if root_x != root_y:
                parent[max(root_x, root_y)] = min(root_x, root_y)

        runs_by_row = {}
        for i, row_id in enumerate(run_row):
            runs_by_row.setdefault(row_id, []).append(i)

        # Only look forwards: the relation is symmetric
        for row_id, sources in runs_by_row.items():
            for dlat in range(0, dlat_max + 1):
                targets = runs_by_row.get(row_id + dlat)
                if not targets:
                    continue
                width = self._column_width(row_id, row_id + dlat, radius_km)
                if width < 0:
                    continue
                for i in sources:
                    a_lo, a_hi = run_lo[i], run_hi[i]
                    for j in targets:
                        if dlat == 0 and j <= i:
                            continue
                        if find(i) == find(j):
                            continue
                        b_lo, b_hi = run_lo[j], run_hi[j]
                        if a_lo <= b_hi and b_lo <= a_hi:
                            gap = 0  # the two column ranges overlap
                        else:
                            gap = min((b_lo - a_hi) % lon_len,
                                      (a_lo - b_hi) % lon_len)
                        if gap <= width:
                            union(i, j)

        # --- Number the clusters ----------------------------------------
        roots = np.array([find(i) for i in range(n_runs)], dtype=np.int64)
        firsts = np.array(run_first, dtype=np.int64)

        lowest_point = np.full(n_runs, np.iinfo(np.int64).max, dtype=np.int64)
        np.minimum.at(lowest_point, roots, firsts)

        live = np.unique(roots)
        cluster_of_root = np.full(n_runs, -1, dtype=np.int64)
        cluster_of_root[live[np.argsort(lowest_point[live], kind="stable")]] = (
            np.arange(len(live), dtype=np.int64)
        )
        run_cluster = cluster_of_root[roots]

        for i in range(n_runs):
            labels[run_first[i]:run_first[i] + run_len[i]] = run_cluster[i]

        # --- Attach the border points -----------------------------------
        # A point that is not itself core still joins the cluster of any core
        # point within the radius. Working outwards from each run covers all
        # of them at once: the columns it can reach are one interval.
        noncore_by_row = {}
        for k, row_id in enumerate(row_ids):
            row_from, row_to = row_starts[k], row_ends[k]
            in_row = np.flatnonzero(~is_core[row_from:row_to])
            if len(in_row):
                noncore_by_row[int(row_id)] = (
                    i_lons[row_from:row_to][in_row], row_from + in_row
                )

        claimed = np.full(n_points, np.iinfo(np.int64).max, dtype=np.int64)
        for j in range(n_runs):
            row_id = run_row[j]
            for dlat in range(-dlat_max, dlat_max + 1):
                entry = noncore_by_row.get(row_id + dlat)
                if entry is None:
                    continue
                width = self._column_width(row_id, row_id + dlat, radius_km)
                if width < 0:
                    continue
                cols, point_idx = entry
                extended = np.concatenate(
                    (cols - lon_len, cols, cols + lon_len)
                )
                lo = np.searchsorted(extended, run_lo[j] - width, side="left")
                hi = np.searchsorted(extended, run_hi[j] + width, side="right")
                if hi > lo:
                    np.minimum.at(
                        claimed, np.tile(point_idx, 3)[lo:hi], run_cluster[j]
                    )

        borders = claimed < np.iinfo(np.int64).max
        labels[borders] = claimed[borders]

        return labels

    def _finalize_cluster(self, ev):
        """
        Finalize a completed event and write output files.

        Applies land/ocean filtering (which mutates the eventlet, and so only
        happens once the event is complete), then writes two output files:

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

        full_event, catalogue_event = self._build_event(ev, provisional=False)

        year = all_times[0].strftime('%Y')
        catalogue_path = f"{self.output_path}/events-{self.eventtype}-{year}.jsonl"
        event_path = f"{self.output_path}/events/event-{full_event['id']}.json"

        with open(catalogue_path, "a") as f:
            f.write(json.dumps(round_floats(catalogue_event)) + "\n")

        with open(event_path, "w") as f:
            f.write(json.dumps(round_floats(full_event)) + "\n")

    def _build_event(self, ev, provisional):
        """
        Build the serialisable payloads describing an eventlet.

        Generates comprehensive metadata including:
        - Temporal information (times, duration)
        - Spatial information (geometries, centroids, bounding box)
        - Statistical summaries (max/mean/min values)
        - Per-pixel maximum values
        - Land/ocean classification

        This is read-only with respect to ``ev`` so it can be called repeatedly
        on an event that is still growing. Because an active event is rebuilt
        on every time step whether or not it moved, the result is memoised
        against the identity of the event's slice arrays: an event that was not
        extended this step costs nothing to republish.

        Args:
            ev: Eventlet object to describe
            provisional: True if the event is still active and may yet change

        Returns:
            Tuple of (full_event, catalogue_event) dictionaries
        """
        cached = getattr(ev, "_payload_cache", None)
        if (
            cached is not None
            and cached[1] == provisional
            and len(cached[0]) == len(ev.slices)
            and all(a is b for a, b in zip(cached[0], ev.slices))
        ):
            return cached[2], cached[3]
        slices_snapshot = tuple(ev.slices)

        all_times = sorted([pd.Timestamp(t) for t in ev.times])
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
                if len(ev.slices[i]) > 0:
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

        # Compute overall event geometry. Extending an event usually does not
        # change its footprint — new points mostly land on pixels it already
        # covers — so key the cached shape on the footprint itself rather than
        # on whether the event grew.
        footprint_key = unique_coords.tobytes()
        footprint_cache = getattr(ev, "_footprint_cache", None)
        if (
            footprint_cache is not None
            and footprint_cache[0] == footprint_key
            and footprint_cache[1] == provisional
        ):
            total_region = footprint_cache[2]
        elif provisional:
            # An alpha shape over the whole accumulated footprint is by far the
            # most expensive part of building a payload, and for a growing
            # event it has to be redone almost every step. Union the per-slice
            # hulls instead, which are already cached. The result is the region
            # the event has swept rather than a fresh concave hull over every
            # point, so it is slightly more conservative where an event moved
            # far between steps. Finished events still get the exact shape.
            shapes = [s for s in (ev.hull(i) for i in range(len(ev.slices)))
                      if s is not None]
            total_region = get_region(unary_union(shapes) if shapes else None)
            ev._footprint_cache = (footprint_key, provisional, total_region)
        else:
            total_region = get_region(safe_alphashape(unique_coords, alpha=1.0))
            ev._footprint_cache = (footprint_key, provisional, total_region)

        # Build full event dictionary
        full_event = {
            "id": event_id,
            "event_type": self.eventtype,
            "provisional": provisional,
            "times": [format_time(t) for t in all_times],
            "regions": [ev.region(i) for i in range(len(ev.slices))],
            "total_region": total_region,
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
            "provisional": provisional,
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

        ev._payload_cache = (
            slices_snapshot, provisional, full_event, catalogue_event
        )
        return full_event, catalogue_event


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
    ["stat", "perc", "thresh", "nr", "ms", "event_mode"]
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
        event_mode: 'hot', 'cold', or 'wet'
    """
    return [
        ParamSet(
            stat="min",
            perc="2.0",
            thresh=0,
            nr=250,
            ms=60,
            event_mode='cold'
        ),
        ParamSet(
            stat="max",
            perc="98.0",
            thresh=28,
            nr=250,
            ms=60,
            event_mode='hot'
        ),
        ParamSet(
            stat="tp",
            perc="95.0",
            thresh=0.0,
            nr=250,
            ms=60,
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
        
        # Generate parameter string for filenames. The clustering segment is
        # fixed now that DBSCAN is the only option, kept so that filenames stay
        # comparable with earlier runs.
        param_str = (
            f"{param.stat}-{param.perc}-{param.thresh if param.thresh is not None else 'iqr'}-"
            f"nr{param.nr}-ms{param.ms}-"
            f"dbscan-"
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
            last_slice_name=f"{out_path}/last_slice-{param_str}.pkl",
            eventtype=param.event_mode,
            land_only=land_sea_mask is not None
        )
        logger.info(f"{out_path}/last_slice-{param_str} ,_ last slice")

        # Without resume state the record is replayed from the beginning, so
        # whatever a previous pass appended is about to be written again.
        if factory.skipToTime is None:
            factory.reset_catalogues()

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
