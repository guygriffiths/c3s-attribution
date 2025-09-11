#!/usr/bin/env python3

from matplotlib.patches import Polygon
import numpy as np
from sklearn.cluster import DBSCAN
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
import xarray as xr
from collections import deque
import xarray as xr
import numpy as np
from scipy.ndimage import label, binary_erosion
from datetime import timedelta
from shapely.geometry import MultiPoint
from shapely.ops import unary_union
import json
import queue
import alphashape


def walk_scan(D_coo: coo_matrix, eps: float, min_samples: int = 1):
    """
    Sparse distance-matrix DBSCAN drop-in replacement.
    Takes:
        D_coo: sparse COO matrix of distances between valid pairs
        eps: distance threshold
        min_samples: minimum cluster size (remove smaller ones at end)

    Returns:
        labels: np.ndarray of cluster labels (-1 for noise)
    """
    D = D_coo.tocsr()
    n_points = D.shape[0]
    visited = np.zeros(n_points, dtype=bool)
    labels = -np.ones(n_points, dtype=int)
    cluster_id = 0

    for i in range(n_points):
        if visited[i]:
            continue

        # Find neighbours within eps
        neighbours = D[i].indices[D[i].data <= eps]

        # Start new cluster
        queue = deque([i])
        queue.extend(neighbours)
        cluster_members = set()

        while queue:
            point = queue.popleft()
            if visited[point]:
                continue
            visited[point] = True
            cluster_members.add(point)

            # Expand neighbours
            neighbours = D[point].indices[D[point].data <= eps]
            if len(neighbours) >= min_samples:
                queue.extend(neighbours)

        # Drop small clusters
        if len(cluster_members) >= min_samples:
            for pt in cluster_members:
                labels[pt] = cluster_id
            cluster_id += 1

    return labels


def get_region(shape):
    if shape.geom_type == "Polygon":
        return [[x, y] for x, y in shape.exterior.coords]
    else:
        minx, miny, maxx, maxy = shape.bounds
        pad = 0.125
        return [
            [minx - pad, miny - pad],
            [minx - pad, maxy + pad],
            [maxx + pad, maxy + pad],
            [maxx + pad, miny - pad],
            [minx - pad, miny - pad],
        ]


import numpy as np

def safe_alphashape(points, alpha=1.0):
    if points is None or len(points) == 0:
        return None

    try:
        shape = alphashape.alphashape(points, alpha)
        if shape and not shape.is_empty:
            return shape
    except Exception:
        pass

    # Fallbacks
    if len(points) == 1:
        x, y = points[0]
        return Polygon([
            (x-0.125, y-0.125), (x+0.125, y-0.125),
            (x+0.125, y+0.125), (x-0.125, y+0.125)
        ])
    elif len(points) == 2:
        return MultiPoint(points).buffer(0.125)  # wee fat line
    else:
        return MultiPoint(points).convex_hull  # co-linear or failed alpha


class Eventlet:
    def __init__(self, time, coords, values):
        self.times = [time]
        # Expecting coords as a list of (lat, lon) tuples or a NumPy array
        self.slices = [np.array(coords, dtype=np.float32)]  # list of (N, 2) arrays
        self.values = [values]

    def last_time(self):
        return self.times[-1]

    def earliest_time(self):
        return self.times[0]

    def centroid(self, n):
        if not self.slices:
            return None
        target_slice = self.slices[n] if n < len(self.slices) else self.slices[-1]
        if len(target_slice) == 0:
            return None
        lat_mean = np.mean(target_slice[:, 0])
        lon_mean = np.mean(target_slice[:, 1])
        return (lat_mean, lon_mean)

    def hull(self, n, alpha=1.0):
        if not self.slices:
            return None
        target_slice = self.slices[n] if n < len(self.slices) else self.slices[-1]
        if len(target_slice) == 0:
            return None

        longitude_span = target_slice[:, 1].max() - target_slice[:, 1].min()
        if longitude_span > 180:
            target_slice = target_slice.copy()
            target_slice[:, 1] = np.where(
                target_slice[:, 1] < 0, target_slice[:, 1] + 360, target_slice[:, 1]
            )

        return safe_alphashape(target_slice, alpha)


    def overlaps(self, coords, eps=1e-6):
        test = np.array(coords, dtype=np.float32)  # shape (N, 2)
        current = self.slices[-1]  # shape (M, 2)

        # Compute pairwise absolute differences for lat and lon
        # Broadcast shapes: (N,1,2) and (1,M,2) -> (N,M,2)
        diffs = np.abs(test[:, None, :] - current[None, :, :])

        # Check if differences in both lat & lon are < eps
        close_points = np.all(diffs < eps, axis=2)  # shape (N, M), True if points close

        # Check if any pair is close
        return np.any(close_points)

    def extend(self, time, coords, values):
        coords_arr = np.array(coords, dtype=np.float32)
        values_arr = np.array(values, dtype=np.float32)
        if time in self.times:
            idx = self.times.index(time)
            self.slices[idx] = np.vstack((self.slices[idx], coords_arr))
            self.values[idx] = np.concatenate((self.values[idx], values_arr))
        else:
            self.times.append(time)
            self.slices.append(coords_arr)
            self.values.append(values_arr)

        # Keep times + slices sorted
        sorted_triplets = sorted(
            zip(self.times, self.slices, self.values), key=lambda x: x[0]
        )
        self.times, self.slices, self.values = map(list, zip(*sorted_triplets))

    def merge(self, other):
        time_to_idx = {t: i for i, t in enumerate(self.times)}

        for t, other_slice, other_val in zip(other.times, other.slices, other.values):
            if t in time_to_idx:
                i = time_to_idx[t]
                # print(f"Merging slice at {t} with existing slice {self.times[i]}")
                # print(
                #     f"Slice:\n{self.slices[i]}\nOther:\n{other_slice}\nValues:\n{self.values[i]}\nOther:\n{other_val}\n\n"
                # )
                self.slices[i] = np.vstack((self.slices[i], other_slice))
                # print(f"Slice result:\n{self.slices[i]}\n")
                self.values[i] = np.concatenate((self.values[i], other_val))
                # print(f"Values result:\n{self.values[i]}\n")
            else:
                self.times.append(t)
                self.slices.append(other_slice.copy())
                self.values.append(other_val.copy())

        # Re-sort all three by time
        sorted_triplets = sorted(
            zip(self.times, self.slices, self.values), key=lambda x: x[0]
        )
        self.times, self.slices, self.values = map(list, zip(*sorted_triplets))

    def is_expired(self, oldest_upstream_time, time_threshold):
        time_threshold = pd.Timedelta(time_threshold)  # ensures compatibility
        return (self.last_time() + time_threshold) < oldest_upstream_time

    def is_valid(self, min_length):
        # Check if the eventlet has enough slices
        if len(self.slices) < min_length:
            return False
        # Check if the last slice has enough points
        if len(self.slices[-1]) < min_length:
            return False
        return True

    def clear(self):
        self.times.clear()
        self.slices.clear()


class EventletFactory:
    def __init__(
        self,
        data,
        threshold,
        ref_data,
        land_sea_mask=None,
        expiry_days=1,
        min_length=3,
        neighbor_radius=4.5,
        output_path="/data/output-debug/events",
        use_dbscan=False,
    ):
        self.data = data
        self.threshold = threshold
        self.ref_data = ref_data
        self.land_sea_mask = land_sea_mask
        self.expiry_days = expiry_days
        self.min_length = min_length
        self.active = []
        self.output_queue = deque()
        self.oldest_active_time = None
        self.id = 0
        self.radius = neighbor_radius
        self.output_path = output_path
        self.use_dbscan = use_dbscan

        self.raw_mask = (data > self.threshold) & (data > ref_data)

        self.enduring_pixels = (
            self.raw_mask.rolling(valid_time=3, center=True).sum().fillna(0) >= 3
        )

        # Store the full thresholded mask
        self.raw_mask = (
            (data > self.threshold) & (data > ref_data)
        ).values  # shape (T, Y, X), bool
        # print(f"Raw mask shape: {self.raw_mask.shape}")

        self.times = self.data.valid_time.values  # in __init__

    def process_slice(self, time):
        # print(f"Processing slice at {time}")

        data_slice = self.data.sel(
            valid_time=time
        ).load()  # Load the slice for the given time
        t = np.searchsorted(self.times, np.datetime64(time))

        raw_mask_slice = self.raw_mask[t].copy()
        enduring_slice = np.where(self.enduring_pixels[t], raw_mask_slice, False)

        hot_indices = np.argwhere(
            enduring_slice
        )  # shape (N, 2): rows are (i_lat, i_lon)

        lat_vals = data_slice.latitude.values  # shape (Y,)
        lon_vals = data_slice.longitude.values  # shape (X,)

        D, metadata = self.get_distance_matrix(
            hot_indices, lat_vals, lon_vals, radius=self.radius
        )

        if not self.use_dbscan:
            labels = walk_scan(D, eps=1.5, min_samples=1)
        else:
            db = DBSCAN(
                eps=1.5,
                min_samples=1,
                metric="precomputed",
            )
            labels = db.fit_predict(D)

        blobs = []
        for label in set(labels):
            points = [m for i, m in enumerate(metadata) if labels[i] == label]
            blobs.append(points)

        # Now we have full list of blobs in this time slice

        print(f"Found {len(blobs)} potential events in slice at {time}")

        used_blobs = set()
        for i, blob in enumerate(blobs):
            matched = False
            for ev in self.active:
                if ev.overlaps(blob):
                    values = [
                        data_slice.sel(latitude=lat, longitude=lon).values.item()
                        for lat, lon in blob
                    ]
                    ev.extend(time, blob, values)
                    used_blobs.add(i)
                    matched = True
                    break
            if not matched:
                values = [
                    data_slice.sel(latitude=lat, longitude=lon).values.item()
                    for lat, lon in blob
                ]
                new_ev = Eventlet(time, blob, values)
                self.active.append(new_ev)

        # Expire any events that are too old
        for ev in list(self.active):  # copy to avoid mutation during loop
            if ev.is_expired(time, self.expiry_days):
                if ev.is_valid(self.min_length):
                    self._finalise_cluster(ev)
                self.active.remove(ev)

        # Sort active events largest-first (for later matching)
        self.active.sort(key=lambda ev: len(ev.values), reverse=True)

        # Update oldest time
        self.oldest_active_time = min(
            (ev.earliest_time() for ev in self.active), default=None
        )

    def flush(self):
        for ev in self.active:
            self.output_queue.append(ev)
        self.active = []

    def yield_completed(self):
        while self.output_queue:
            yield self.output_queue.popleft()

    def get_distance_matrix(self, coords, lat_arr, lon_arr, radius=4.5):
        lat_len = len(lat_arr)
        lon_len = len(lon_arr)

        metadata = []
        metadata_index = {}

        coord_set = set(map(tuple, coords))

        def get_uid(i_lat, i_lon):
            return i_lat * lon_len + i_lon

        def ensure_metadata(i_lat, i_lon):
            uid = get_uid(i_lat, i_lon)
            if uid not in metadata_index:
                metadata_index[uid] = len(metadata)
                metadata.append((float(lat_arr[i_lat]), float(lon_arr[i_lon])))
            return metadata_index[uid]

        p1idx = []
        p2idx = []

        radius_ceiling = int(np.ceil(radius))
        delta_list = np.arange(-radius_ceiling, radius_ceiling + 1, 1)

        for i_lat, i_lon in coords:
            i_idx = ensure_metadata(i_lat, i_lon)
            for dlat in delta_list:
                for dlon in delta_list:
                    if (
                        dlat == 0
                        and dlon == 0
                        or dlat * dlat + dlon * dlon > radius * radius
                    ):
                        continue
                    j_lat = i_lat + dlat
                    j_lon = (i_lon + dlon) % lon_len

                    if 0 <= j_lat < lat_len and (j_lat, j_lon) in coord_set:
                        j_idx = metadata_index.get(get_uid(j_lat, j_lon))
                        if j_idx is not None:
                            p1idx.append(i_idx)
                            p2idx.append(j_idx)

        dists = [1] * len(p1idx)
        D = coo_matrix((dists, (p1idx, p2idx)), shape=(len(metadata), len(metadata)))
        D = D + D.T
        return D, metadata

    def _finalise_cluster(self, ev):
        # print(f"Finalising cluster with {ev}\n")
        all_times = sorted(ev.times)
        centroids = []

        all_coords = []

        for i, region in enumerate(ev.slices):
            latlons = [(float(lat), float(lon)) for lat, lon in region]
            all_coords.extend(latlons)

            lats, lons = zip(*latlons)
            centroids.append(ev.centroid(i))

        lats, lons = zip(*all_coords)
        bbox = [float(min(lats)), float(min(lons)), float(max(lats)), float(max(lons))]

        event_id = get_id(all_times[0], centroids[0])
        peak_values = to_serialisable(
            [
                np.max(ev.values[i]) if len(ev.values[i]) > 0 else None
                for i in range(len(ev.slices))
            ]
        )
        peak_value = to_serialisable(np.max(peak_values)) if peak_values else None
        mean_values = to_serialisable(
            [
                np.mean(ev.values[i]) if len(ev.values[i]) > 0 else None
                for i in range(len(ev.slices))
            ]
        )
        mean_value = to_serialisable(np.mean(np.concatenate(ev.values))) if mean_values else None

        ocean_only = False
        if self.land_sea_mask is not None:
            all_ocean = True
            lat_asc = np.all(np.diff(self.land_sea_mask.latitude) > 0)
            lats = self.land_sea_mask.latitude.values
            if not lat_asc:
                lats = lats[::-1]  # ascending for searchsorted

            for i in range(len(ev.slices)):
                if ev.hull(i) is not None:
                    coords = np.array(ev.slices[i])
                    # Latitude indices
                    lat_indices = np.searchsorted(lats, coords[:, 0])
                    lat_indices = np.clip(lat_indices, 0, self.land_sea_mask.latitude.size - 1)
                    if not lat_asc:
                        lat_indices = self.land_sea_mask.latitude.size - 1 - lat_indices

                    # Longitude indices
                    lon_indices = np.searchsorted(self.land_sea_mask.longitude, coords[:, 1])
                    lon_indices = np.clip(lon_indices, 0, self.land_sea_mask.longitude.size - 1)

                    mask_values = self.land_sea_mask.values[0, lat_indices, lon_indices]
                    if not np.all(mask_values == 0):
                        all_ocean = False
                        break
            ocean_only = all_ocean


        if ocean_only:
            print(f"Event {event_id} is ocean-only, with centroid {centroids[0]}")
        
        # ensure arrays are 1-D and aligned
        all_coords = np.vstack([np.asarray(t_slice) for t_slice in ev.slices])  # (N, 2)
        all_values = np.hstack([np.asarray(vals).ravel() for vals in ev.values])  # (N,)

        if all_coords.shape[0] != all_values.shape[0]:
            raise ValueError(f"mismatch: {all_coords.shape[0]} coords vs {all_values.shape[0]} values")

        # structured view & grouping
        coords_view = all_coords.view([('', all_coords.dtype)] * all_coords.shape[1]).ravel()
        unique_coords, inverse_idx = np.unique(coords_view, return_inverse=True)

        # compute per-pixel max
        pixel_peak_values = np.full(len(unique_coords), -np.inf, dtype=all_values.dtype)
        # print(all_coords.shape, all_values.shape, inverse_idx.shape, pixel_peak_values.shape)
        np.maximum.at(pixel_peak_values, inverse_idx, all_values)


        # Convert back to normal ndarray
        unique_coords = unique_coords.view(all_coords.dtype).reshape(-1, all_coords.shape[1])
        pixel_set = unique_coords.tolist()

        full_event = {
            "id": event_id,
            "times": [formatTime(t) for t in all_times],
            "regions": [get_region(ev.hull(i)) for i in range(len(ev.slices))],
            "total_region": get_region(
                unary_union([ev.hull(i) for i in range(len(ev.slices)) if ev.hull(i)])
            ),
            "slices": to_serialisable(ev.slices),
            "values": to_serialisable(ev.values),
            "centroids": to_serialisable(centroids),
            "bbox": to_serialisable(bbox),
            "total_area": float(
                unary_union(
                    [
                        ev.hull(i)
                        for i in range(len(ev.slices))
                        if ev.hull(i) is not None
                    ]
                ).area
            ),
            "areas": to_serialisable(
                [
                    ev.hull(i).area if ev.hull(i) is not None else 0
                    for i in range(len(ev.slices))
                ]
            ),
            "peak_values": peak_values,
            "peak_value": peak_value,
            "mean_values": mean_values,
            "mean_value": mean_value,
            "ocean_only": ocean_only,
            "pixel_set": pixel_set,
            "pixel_count": len(pixel_set),
            "pixel_peak_values": to_serialisable(pixel_peak_values),
        }

        catalogue_event = {
            "id": full_event["id"],
            "times": full_event["times"],
            "regions": full_event["regions"],
            "total_region": full_event["total_region"],
            "bbox": full_event["bbox"],
            "peak_value": (
                np.max(full_event["peak_values"]) if full_event["peak_values"] else None
            ),
            "mean_value": (
                np.mean(full_event["mean_values"])
                if full_event["mean_values"]
                else None
            ),
            "total_area": full_event["total_area"],
            "ocean_only": ocean_only,
            "pixel_set": pixel_set,
        }

        with open(f"{self.output_path}/events.jsonl", "a") as f:
            f.write(json.dumps(round_floats(catalogue_event)) + "\n")
        with open(f"{self.output_path}/events/event-{event_id}.json", "w") as f:
            f.write(json.dumps(round_floats(full_event)) + "\n")


def formatTime(t):
    if isinstance(t, np.datetime64):
        return np.datetime_as_string(t, unit="s") + "Z"
    elif isinstance(t, pd.Timestamp):
        return t.isoformat() + "Z"
    elif isinstance(t, str):
        return t + "Z"
    else:
        raise ValueError(f"Unsupported time type: {type(t)}")


import hashlib


def to_serialisable(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, (list, tuple)):
        return [to_serialisable(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: to_serialisable(v) for k, v in obj.items()}
    else:
        return obj


def round_floats(obj):
    if isinstance(obj, float):
        return round(obj, 4)
    elif isinstance(obj, dict):
        return {k: round_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [round_floats(x) for x in obj]
    else:
        return obj


def stable_cluster_hash(time, centroid):
    """
    Stable 32-bit integer hash based on time and centroid.
    Safe for JavaScript and anything else that isnae mad.
    """
    s = f"{str(time)}_{centroid[0]:.6f}_{centroid[1]:.6f}"
    hash_bytes = hashlib.sha256(s.encode("utf-8")).digest()
    return int.from_bytes(hash_bytes[:4], byteorder="big")  # 32 bits

def get_id(time, centroid):
    """
    Generate a stable ID for an event based on time and centroid.
    This is a simple hash function that combines the time and centroid coordinates.
    """
    # snap to nearest 0.001°
    lat = round(centroid[0], 3)
    lon = round(centroid[1], 3)

    # shift negatives to positives
    lat_code = int(round((lat + 90) * 1000))   # 0 → 180000 range
    lon_code = int(round((lon + 180) * 1000))  # 0 → 360000 range

    return f"{time.strftime('%Y%m%d')}{lat_code:06d}{lon_code:06d}"


def downstream_worker(q, clusterer):
    while True:
        ev = q.get()
        if ev is None:
            break  # shutdown signal
        clusterer.process_eventlet(ev)
        q.task_done()


def load_data(data_path, ref_path, land_sea_mask_path):
    ds = xr.open_mfdataset(data_path)
    ref = xr.open_dataset(ref_path)
    if land_sea_mask_path:
        land_sea_mask = xr.open_dataset(land_sea_mask_path)
    else:
        land_sea_mask = None

    def shift_longitudes(da):
        da = da.assign_coords(longitude=(((da.longitude + 180) % 360) - 180))
        return da.sortby("longitude")

    return (
        shift_longitudes(ds["t2m"]),
        shift_longitudes(ref["t2m"]),
        shift_longitudes(land_sea_mask["lsm"]) if land_sea_mask is not None else None,
    )


import os


def main():

    # for dbscan in [False, True]:
    #     for perc in [98, 99]:
    stat = 'max'
    perc = '99.0'
    thresh = 28
    nr = 6


    data_var, ref_data, land_sea_mask = load_data(
        f"/data/era5_2024.nc",
        f"/data/era5_ref98.nc",
        None
    )
    time_dim = data_var["valid_time"]
    out_path = f"/data/output-{stat}-{perc}-{thresh}-nr{nr}"
    os.makedirs(out_path, exist_ok=True)
    os.makedirs(f"{out_path}/events", exist_ok=True)

    factory = EventletFactory(
        data_var,
        threshold=273.15 + thresh,
        ref_data=ref_data,
        land_sea_mask=land_sea_mask,
        neighbor_radius=nr,
        output_path=out_path,
        use_dbscan=False,
    )

    for i in range(time_dim.size):
        time_val = pd.to_datetime(time_dim[i].values)
        factory.process_slice(time_val)

    factory.flush()


if __name__ == "__main__":
    import pandas as pd

    main()
