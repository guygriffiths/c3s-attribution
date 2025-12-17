#!/usr/bin/env python3
import pandas as pd
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
import alphashape
import pickle
import math

R = 6371.0088
def haversine_fast(ll1, ll2):
    # Mean Earth radius in km
    # Convert degrees → radians
    lat1, lon1 = map(math.radians, ll1)
    lat2, lon2 = map(math.radians, ll2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat * 0.5)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon * 0.5)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

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
        return [[[x, y] for x, y in shape.exterior.coords]]
    elif shape.geom_type == "MultiPolygon":
        merged = unary_union(shape)
        if merged.geom_type == "Polygon":
            return [[[x, y] for x, y in merged.exterior.coords]]
        else:  # still MultiPolygon
            return [
                [[x, y] for x, y in poly.exterior.coords]
                for poly in merged.geoms
            ]
    else:
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

import numpy as np


def safe_alphashape(
    points, alpha=1.0, max_attempts=5, growth=2.0, fallback_buffer=0.125
):
    if points is None or len(points) == 0:
        return []
    
    longitude_span = points[:, 1].max() - points[:, 1].min()
    if longitude_span > 180:
        # print("Handling longitude wrap for hull calculation",longitude_span)
        points = points.copy()
        points[:, 1] = np.where(
            points[:, 1] < 0, points[:, 1] + 360, points[:, 1]
        )

    # Try alpha growth
    for i in range(max_attempts):
        try:
            shape = alphashape.alphashape(points, alpha)
            if shape and not shape.is_empty:
                return shape
        except Exception:
            # print(f"Alphashape failed on attempt {i+1} with alpha={alpha}")
            pass
        alpha *= growth  # grow alpha each retry

    # Fallbacks as before...
    n = len(points)
    if n == 1:
        x, y = points[0]
        # print("Alphashape failed, falling back to buffered point")
        return Polygon(
            [
                (x - fallback_buffer, y - fallback_buffer),
                (x + fallback_buffer, y - fallback_buffer),
                (x + fallback_buffer, y + fallback_buffer),
                (x - fallback_buffer, y + fallback_buffer),
            ]
        )
    elif n == 2:
        # print("Alphashape failed, falling back to buffered line")
        return MultiPoint(points).buffer(fallback_buffer)
    else:
        # print("Alphashape failed, falling back to buffered convex hull")
        mp = MultiPoint(points)
        convex = mp.convex_hull
        if convex.is_empty:
            return None
        x_vals, y_vals = zip(*points)
        spread = max(max(x_vals) - min(x_vals), max(y_vals) - min(y_vals))
        buffer_size = min(fallback_buffer, spread * 0.05)
        return convex.buffer(buffer_size)


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

    def remove_ocean(self, land_sea_mask):
        if land_sea_mask is None:
            return

        lat_asc = np.all(np.diff(land_sea_mask.latitude) > 0)
        lats = land_sea_mask.latitude.values
        if not lat_asc:
            lats = lats[::-1]  # ascending for searchsorted

        for i in range(len(self.slices)):
            if self.hull(i) is not None:
                coords = np.array(self.slices[i])
                # Latitude indices
                lat_indices = np.searchsorted(lats, coords[:, 0])
                lat_indices = np.clip(
                    lat_indices, 0, land_sea_mask.latitude.size - 1
                )
                if not lat_asc:
                    lat_indices = land_sea_mask.latitude.size - 1 - lat_indices

                # Longitude indices
                lon_indices = np.searchsorted(land_sea_mask.longitude, coords[:, 1])
                lon_indices = np.clip(
                    lon_indices, 0, land_sea_mask.longitude.size - 1
                )

                mask_values = land_sea_mask.values[0, lat_indices, lon_indices]
                land_points = mask_values != 0

                self.slices[i] = coords[land_points]
                self.values[i] = np.array(self.values[i])[land_points]

        # Remove any empty slices
        non_empty_indices = [i for i in range(len(self.slices)) if len(self.slices[i]) > 0]
        self.times = [self.times[i] for i in non_empty_indices]
        self.slices = [self.slices[i] for i in non_empty_indices]
        self.values = [self.values[i] for i in non_empty_indices]

    def remove_land(self, land_sea_mask):
        if land_sea_mask is None:
            return

        lat_asc = np.all(np.diff(land_sea_mask.latitude) > 0)
        lats = land_sea_mask.latitude.values
        if not lat_asc:
            lats = lats[::-1]  # ascending for searchsorted

        for i in range(len(self.slices)):
            if self.hull(i) is not None:
                coords = np.array(self.slices[i])
                # Latitude indices
                lat_indices = np.searchsorted(lats, coords[:, 0])
                lat_indices = np.clip(
                    lat_indices, 0, land_sea_mask.latitude.size - 1
                )
                if not lat_asc:
                    lat_indices = land_sea_mask.latitude.size - 1 - lat_indices

                # Longitude indices
                lon_indices = np.searchsorted(land_sea_mask.longitude, coords[:, 1])
                lon_indices = np.clip(
                    lon_indices, 0, land_sea_mask.longitude.size - 1
                )

                mask_values = land_sea_mask.values[0, lat_indices, lon_indices]
                ocean_points = mask_values != 1

                self.slices[i] = coords[ocean_points]
                self.values[i] = np.array(self.values[i])[ocean_points]

        # Remove any empty slices
        non_empty_indices = [i for i in range(len(self.slices)) if len(self.slices[i]) > 0]
        self.times = [self.times[i] for i in non_empty_indices]
        self.slices = [self.slices[i] for i in non_empty_indices]
        self.values = [self.values[i] for i in non_empty_indices]


class EventletFactory:
    def __init__(
        self,
        data,
        ref_data,
        threshold,
        over_threshold=True,
        land_sea_mask=None,
        expiry_days=1,
        min_length=3,
        neighbor_radius=200,
        min_samples=1,
        output_path="/data/output-debug/events",
        use_dbscan=False,
        last_slice=None,
        eventtype='hot',
        land_only=False,
        ocean_only=False,
    ):
        self.data = data
        self.threshold = threshold
        self.over_threshold = over_threshold
        self.ref_data = ref_data
        self.land_sea_mask = land_sea_mask
        self.expiry_days = expiry_days
        self.min_length = min_length
        self.min_samples = min_samples
        self.active = []
        self.output_queue = deque()
        self.oldest_active_time = None
        self.id = 0
        self.radius = neighbor_radius
        self.output_path = output_path
        self.use_dbscan = use_dbscan
        self.eventtype = eventtype
        self.land_only = land_only
        self.ocean_only = ocean_only

        # Store the full thresholded mask
        if self.over_threshold:
            self.raw_mask = (
                (data > self.threshold) & (data > ref_data)
            )  # shape (T, Y, X), bool
        else:
            self.raw_mask = (
                (data <= self.threshold) & (data <= ref_data)
            )
        # print(f"Raw mask shape: {self.raw_mask.shape}")

        self.enduring_pixels = (
            self.raw_mask.rolling(valid_time=3, center=True).sum().fillna(0) >= 3
        )
        self.raw_mask = self.raw_mask.values  # convert to NumPy array for speed

        self.times = self.data.valid_time.values  # in __init__

        self.skipToTime = None
        # If we have a last_slice, load it
        if last_slice:
            print(f"Resuming from last slice at {last_slice['time']}")
            self.skipToTime = last_slice['time']
            self.active = last_slice.get("active_events", [])
            if self.active:
                self.oldest_active_time = min(ev.earliest_time() for ev in self.active)
            else:
                self.oldest_active_time = None
            print(f"Resumed {len(self.active)} active events")

    def process_slice(self, time):
        # print(f"Processing slice at {time}")
        if self.skipToTime:
            if time < self.skipToTime:
                print(f"Skipping slice at {time}")
                return
            else:
                print(f"Reached skip-to time at {time}, resuming processing")
                self.skipToTime = None

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
            hot_indices, lat_vals, lon_vals, radius_km=self.radius
        )

        if not self.use_dbscan:
            labels = walk_scan(D, eps=self.radius, min_samples=self.min_samples)
        else:
            db = DBSCAN(
                eps=self.radius,
                min_samples=self.min_samples,
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
            for ev in self.active:
                if ev.overlaps(blob):
                    values = [
                        data_slice.sel(latitude=lat, longitude=lon).values.item()
                        for lat, lon in blob
                    ]
                    ev.extend(time, blob, values)
                    used_blobs.add(i)
                    break

        # Create new eventlets for unmatched blobs
        for i, blob in enumerate(blobs):
            if i in used_blobs:
                continue
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
        self.active.sort(key=lambda ev: len(ev.values[-1]), reverse=True)

        # Update oldest time
        self.oldest_active_time = min(
            (ev.earliest_time() for ev in self.active), default=None
        )

        # Write out last_slice.json. This is used to resume processing from a point.
        # Useful for interrupted runs and operation on rolling data.
        last_slice = {
            "time": time,
            "active_events": self.active,
        }
        with open(f"{self.output_path}/last_slice.pkl", "wb") as f:
            pickle.dump(last_slice, f)

    def flush(self):
        for ev in self.active:
            self.output_queue.append(ev)
        self.active = []

    def yield_completed(self):
        while self.output_queue:
            yield self.output_queue.popleft()

    def get_distance_matrix(self, coords, lat_arr, lon_arr, radius_km=500):
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

        # 0.25 degrees per index step
        res = 0.25
        radius_km_per_deg = 111  # approximate
        radius_deg = radius_km / radius_km_per_deg
        # x2 to ensure we test a bigger area than we want
        delta_coord = 2 * int(np.ceil(radius_deg / res))
        delta_list = np.arange(-delta_coord, delta_coord + 1, 1)

        dists = []
        for i_lat, i_lon in coords:
            i_idx = ensure_metadata(i_lat, i_lon)
            for dlat in delta_list:
                for dlon in delta_list:
                    if (dlat == 0 and dlon == 0):
                        continue
                    j_lat = i_lat + dlat
                    j_lon = (i_lon + dlon) % lon_len

                    if (j_lat, j_lon) in coord_set:
                        d_km = haversine_fast(
                            (lat_arr[i_lat], lon_arr[i_lon]),
                            (lat_arr[j_lat], lon_arr[j_lon])
                        )
                        if d_km <= radius_km:
                            j_idx = ensure_metadata(j_lat, j_lon)
                            p1idx.append(i_idx)
                            p2idx.append(j_idx)
                            dists.append(d_km)

        D = coo_matrix((dists, (p1idx, p2idx)), shape=(len(metadata), len(metadata)))
        D = D + D.T
        return D, metadata

    def _finalise_cluster(self, ev):
        # print(f"Finalising cluster with {ev}\n")
        all_times = sorted(ev.times)
        centroids = []

        all_coords = []

        if self.land_only:
            ev.remove_ocean(self.land_sea_mask)
            if not ev.is_valid(self.min_length):
                print(f"Discarding event at {all_times[0]} for too small over land")
                return
        elif self.ocean_only:
            ev.remove_land(self.land_sea_mask)
            if ev.is_valid(self.min_length):
                print(f"Discarding event at {all_times[0]} for being too small over ocean")
                return

        for i, region in enumerate(ev.slices):
            latlons = [(float(lat), float(lon)) for lat, lon in region]
            all_coords.extend(latlons)

            lats, lons = zip(*latlons)
            centroids.append(ev.centroid(i))

        lats, lons = zip(*all_coords)
        bbox = [float(min(lats)), float(min(lons)), float(max(lats)), float(max(lons))]

        event_id = get_id(self.eventtype, all_times[0], centroids[0], self.threshold, self.radius)
        max_values = to_serialisable(
            [
                np.max(ev.values[i]) if len(ev.values[i]) > 0 else None
                for i in range(len(ev.slices))
            ]
        )
        max_value = to_serialisable(np.max(max_values)) if max_values else None
        mean_values = to_serialisable(
            [
                np.mean(ev.values[i]) if len(ev.values[i]) > 0 else None
                for i in range(len(ev.slices))
            ]
        )
        mean_value = (
            to_serialisable(np.mean(np.concatenate(ev.values))) if mean_values else None
        )
        min_values = to_serialisable(
            [
                np.min(ev.values[i]) if len(ev.values[i]) > 0 else None
                for i in range(len(ev.slices))
            ]
        )
        min_value = to_serialisable(np.min(min_values)) if min_values else None

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
                    lat_indices = np.clip(
                        lat_indices, 0, self.land_sea_mask.latitude.size - 1
                    )
                    if not lat_asc:
                        lat_indices = self.land_sea_mask.latitude.size - 1 - lat_indices

                    # Longitude indices
                    lon_indices = np.searchsorted(
                        self.land_sea_mask.longitude, coords[:, 1]
                    )
                    lon_indices = np.clip(
                        lon_indices, 0, self.land_sea_mask.longitude.size - 1
                    )

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
            raise ValueError(
                f"mismatch: {all_coords.shape[0]} coords vs {all_values.shape[0]} values"
            )

        # structured view & grouping
        coords_view = all_coords.view(
            [("", all_coords.dtype)] * all_coords.shape[1]
        ).ravel()
        unique_coords, inverse_idx = np.unique(coords_view, return_inverse=True)

        # compute per-pixel max
        pixel_max_values = np.full(len(unique_coords), -np.inf, dtype=all_values.dtype)
        # print(all_coords.shape, all_values.shape, inverse_idx.shape, pixel_max_values.shape)
        np.maximum.at(pixel_max_values, inverse_idx, all_values)

        # Convert back to normal ndarray
        unique_coords = unique_coords.view(all_coords.dtype).reshape(
            -1, all_coords.shape[1]
        )
        pixel_set = unique_coords.tolist()
        total_region_shape = safe_alphashape(unique_coords, alpha=1.0)

        full_event = {
            "id": event_id,
            "event_type": self.eventtype,
            "times": [formatTime(t) for t in all_times],
            "regions": [get_region(ev.hull(i)) for i in range(len(ev.slices))],
            "total_region": get_region(total_region_shape),
            "slices": to_serialisable(ev.slices),
            "values": to_serialisable(ev.values),
            "centroids": to_serialisable(centroids),
            "bbox": to_serialisable(bbox),
            "total_area": total_region_shape.area if total_region_shape else 0,
            "areas": to_serialisable(
                [
                    ev.hull(i).area if ev.hull(i) is not None else 0
                    for i in range(len(ev.slices))
                ]
            ),
            "max_values": max_values,
            "max_value": max_value,
            "mean_values": mean_values,
            "mean_value": mean_value,
            "min_values": min_values,
            "min_value": min_value,
            "ocean_only": ocean_only,
            "pixel_set": pixel_set,
            "pixel_count": len(pixel_set),
            "pixel_max_values": to_serialisable(pixel_max_values),
        }

        def packPixelToInt(lat: float, lon: float) -> int:
            iLat = int(np.round(lat * 4))
            while lon < -180:
                lon += 360
            while lon > 180:
                lon -= 360
            iLon = int(np.round(lon * 4))
            return (iLat << 16) | (iLon & 0xffff)

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
            "pixel_set": [packPixelToInt(*coord) for coord in pixel_set],
        }

        with open(f"{self.output_path}/events-{self.eventtype}-{all_times[0].strftime('%Y')}.jsonl", "a") as f:
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


def get_id(eventtype, time, centroid, threshold, radius):
    """
    Generate a stable ID for an event based on time and centroid.
    This is a simple hash function that combines the time and centroid coordinates.
    """
    # snap to nearest 0.001°
    lat = round(centroid[0], 3)
    lon = round(centroid[1], 3)

    # shift negatives to positives
    lat_code = int(round((lat + 90) * 1000))  # 0 → 180000 range
    lon_code = int(round((lon + 180) * 1000))  # 0 → 360000 range

    thresh = int(round(threshold - 273.15)*10)
    if thresh < 0:
        thresh = 900-thresh
    radius = int(round(radius))

    return f"{eventtype}{time.strftime('%Y%m%d')}{thresh:03d}{radius:05d}{lat_code:06d}{lon_code:06d}"


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
    stat = "max"
    perc = "99.0"
    thresh = 28
    nr = 200
    heatwave = True
    
    for ms in [30, 20, 10, 5]:
        for nr in [160, 180, 200, 250]:
            for dbscan in [False, True]:
                data_var, ref_data, land_sea_mask = load_data(
                    f"/data/{stat}/era5_daily_{stat}_temperature*2024.nc",
                    f"/data/climatology/era5_daily_{stat}_temperature_{perc}pc_1991-2020.nc",
                    f"/data/era5_land_sea_mask.nc",
                )
                time_dim = data_var["valid_time"]
                out_path = f"/data/output-{'dbscan' if dbscan else 'walk'}-{ms}-{stat}-{perc}-{thresh}-nr{nr}-{heatwave and 'hw' or 'cw'}"
                os.makedirs(out_path, exist_ok=True)
                os.makedirs(f"{out_path}/events", exist_ok=True)

                last_slice = None
                if os.path.exists(f"{out_path}/last_slice.pkl"):
                    with open(f"{out_path}/last_slice.pkl", "rb") as f:
                        last_slice = pickle.load(f)

                factory = EventletFactory(
                    data_var,
                    ref_data=ref_data,
                    threshold=273.15 + thresh,
                    over_threshold=heatwave,
                    land_sea_mask=land_sea_mask,
                    neighbor_radius=nr,
                    min_samples=ms,
                    output_path=out_path,
                    use_dbscan=False,
                    last_slice=last_slice,
                    eventtype='hot' if heatwave else 'cold',
                    land_only=land_sea_mask is not None,
                )

                for i in range(time_dim.size):
                    time_val = pd.to_datetime(time_dim[i].values)
                    factory.process_slice(time_val)

                factory.flush()


if __name__ == "__main__":
    main()
