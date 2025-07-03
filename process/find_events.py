#!/usr/bin/env python3

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
import json
import queue
import threading


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

    def hull(self, n):
        if not self.slices:
            return None
        target_slice = self.slices[n] if n < len(self.slices) else self.slices[-1]
        if len(target_slice) == 0:
            return None
        return MultiPoint(target_slice).convex_hull

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
        expiry_days=1,
        min_length=3,
        neighbor_weight_fn=None,
    ):
        self.data = data
        self.threshold = threshold
        self.ref_data = ref_data
        self.expiry_days = expiry_days
        self.min_length = min_length
        self.active = []
        self.output_queue = deque()
        self.neighbor_weight_fn = neighbor_weight_fn or (lambda dx, dy: 1)
        self.oldest_active_time = None
        self.id = 0

        # Store the full thresholded mask
        self.raw_mask = (
            (data > self.threshold) & (data > ref_data)
        ).values  # shape (T, Y, X), bool
        # print(f"Raw mask shape: {self.raw_mask.shape}")

        # Ignore any pixels which are not hot for at least 3 time steps
        sliding_sum = np.lib.stride_tricks.sliding_window_view(
            self.raw_mask, window_shape=3, axis=0
        ).sum(
            axis=0
        )  # shape (Y, X)
        self.enduring_pixels = (sliding_sum >= 3).any(axis=2)  # shape (Y, X)

        self.times = self.data.valid_time.values  # in __init__

    def process_slice(self, time):
        print(f"Processing slice at {time}")

        data_slice = self.data.sel(
            valid_time=time
        ).load()  # Load the slice for the given time
        t = np.searchsorted(self.times, np.datetime64(time))

        raw_mask_slice = self.raw_mask[t].copy()
        enduring_slice = np.where(self.enduring_pixels, raw_mask_slice, 0)

        hot_indices = np.argwhere(
            enduring_slice
        )  # shape (N, 2): rows are (i_lat, i_lon)

        lat_vals = data_slice.latitude.values  # shape (Y,)
        lon_vals = data_slice.longitude.values  # shape (X,)

        # coords = np.column_stack(
        #     (
        #         lat_vals[hot_indices[:, 0]],  # i_lat -> actual latitude
        #         lon_vals[hot_indices[:, 1]],  # i_lon -> actual longitude
        #     )
        # )

        D, metadata = self.get_distance_matrix(
            hot_indices, lat_vals, lon_vals, radius=2, eps=1.5, min_samples=1
        )
        db = DBSCAN(
            eps=1.5,
            min_samples=1,
            metric="precomputed",
        )
        labels = db.fit_predict(D)
        # print(f"DBSCAN found {len(set(labels))} clusters in slice at {labels}")
        blobs = []
        for label in set(labels):
            points = [m for i, m in enumerate(metadata) if labels[i] == label]
            blobs.append(points)

        print(f"Found {len(blobs)} blobs in slice at {time}")

        used_blobs = set()

        for ev in self.active:
            matched = False
            for i, blob in enumerate(blobs):
                if ev.overlaps(blob):
                    values = []
                    for lat, lon in blob:
                        val = data_slice.sel(latitude=lat, longitude=lon).values.item()
                        values.append(val)
                    ev.extend(time, blob, values)
                    used_blobs.add(i)
                    matched = True

            if not matched and ev.is_expired(time, self.expiry_days):
                if ev.is_valid(self.min_length):
                    self.output_queue.append(ev)
                # drop otherwise
        self.active = [
            ev for ev in self.active if not ev.is_expired(time, self.expiry_days)
        ]

        for i, blob in enumerate(blobs):
            if i not in used_blobs:
                values = []
                for lat, lon in blob:
                    val = data_slice.sel(latitude=lat, longitude=lon).values.item()
                    values.append(val)
                    # print(f"Adding new eventlet at {time} with {len(blob)} coords {blob}\n and {len(values)} values {values}")
                new_ev = Eventlet(time, blob, values)
                self.active.append(new_ev)

        self.oldest_active_time = min(
            (ev.earliest_time() for ev in self.active), default=None
        )

    def yield_completed(self):
        while self.output_queue:
            yield self.output_queue.popleft()

    def get_distance_matrix(self, coords, lat_arr, lon_arr, radius=2, eps=1.5, min_samples=1):
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

        for i_lat, i_lon in coords:
            i_idx = ensure_metadata(i_lat, i_lon)
            for dlat in [-2, -1, 0, 1, 2]:
                for dlon in [-2, -1, 0, 1, 2]:
                    if dlat == 0 and dlon == 0 or abs(dlat) == 2 and abs(dlon) == 2:
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


class EventletClusterer:
    def __init__(
        self,
        dist_threshold,
        factory_ref,
        time_threshold=timedelta(days=1),
        output_path="/data/output/",
    ):
        self.dist_threshold = dist_threshold
        self.factory = factory_ref
        self.time_threshold = time_threshold
        self.eventlets = []
        self.output_path = output_path

    def custom_distance(self, ev1, ev2):
        ts1 = ev1.times
        ts2 = ev2.times
        idx1 = {t: i for i, t in enumerate(ts1)}
        idx2 = {t: i for i, t in enumerate(ts2)}

        min_dist = np.inf

        for t1 in ts1:
            i1 = idx1[t1]
            hull1 = ev1.hull(i1)

            for offset in [0]:  # [-1, 0, 1]:
                t2 = t1 + timedelta(days=offset)
                i2 = idx2.get(t2)
                if i2 is None:
                    continue

                hull2 = ev2.hull(i2)

                if hull1.intersects(hull2):
                    return 0.0  # Direct intersection or containment

                min_dist = min(min_dist, hull1.distance(hull2))

        return min_dist

    def process_eventlet(self, eventlet):
        self._finalise_cluster(eventlet)
        return
        # print(f"Processing eventlet with {len(eventlet.times)} times\n")
        matched_eventlet = None

        for existing_ev in self.eventlets:
            dist = self.custom_distance(eventlet, existing_ev)
            if dist <= self.dist_threshold:
                matched_eventlet = existing_ev
                break
            if matched_eventlet:
                break

        if matched_eventlet:
            # print(f"Growing stored cluster ({len(self.eventlets)})\n")
            matched_eventlet.merge(eventlet)
        else:
            self.eventlets.append(eventlet)
            # print(f"Adding new cluster ({len(self.eventlets)})\n")

        self._purge_stale()

    def _purge_stale(self):
        active_time = self.factory.oldest_active_time
        # print(f"Purging clusters based on active time: {active_time}\n")
        if active_time is None:
            return  # Nothing active upstream

        cutoff_time = active_time - self.time_threshold
        # print(f"Purging clusters older than {cutoff_time}\n")
        new_clusters = []
        for cluster in self.eventlets:
            cluster_is_active = cluster.last_time() >= cutoff_time
            if cluster_is_active:
                new_clusters.append(cluster)
            else:
                self._finalise_cluster(cluster)
        self.eventlets = new_clusters
        # print(f"Purged down to ({len(self.eventlets)})")

    def _finalise_cluster(self, ev):
        print(f"Finalising cluster with {ev}\n")
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

        event_id = stable_cluster_hash(all_times[0], centroids[0])

        catalogue_event = {
            "id": event_id,
            "times": [t.isoformat() + "Z" for t in all_times],
            "regions": [get_region(ev.hull(i)) for i in range(len(ev.slices))],
            "bbox": to_serialisable(bbox),
        }

        full_event = {
            "id": event_id,
            "times": [t.isoformat() + "Z" for t in all_times],
            "regions": [get_region(ev.hull(i)) for i in range(len(ev.slices))],
            "slices": to_serialisable(ev.slices),
            "values": to_serialisable(ev.values),
            "centroids": to_serialisable(centroids),
            "bbox": to_serialisable(bbox),
        }

        with open(f"{self.output_path}/events.jsonl", "a") as f:
            f.write(json.dumps(round_floats(catalogue_event)) + "\n")
        with open(f"{self.output_path}/events/event-{event_id}.json", "w") as f:
            f.write(json.dumps(round_floats(full_event)) + "\n")


import hashlib


def to_serialisable(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
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


def downstream_worker(q, clusterer):
    while True:
        ev = q.get()
        if ev is None:
            break  # shutdown signal
        clusterer.process_eventlet(ev)
        q.task_done()


def load_data(data_path, ref_path):
    ds = xr.open_mfdataset(data_path)
    ref = xr.open_dataset(ref_path)

    def shift_longitudes(da):
        da = da.assign_coords(longitude=(((da.longitude + 180) % 360) - 180))
        return da.sortby("longitude")

    return shift_longitudes(ds["t2m"]), shift_longitudes(ref["t2m"])


def main():
    data_var, ref_data = load_data("/data/era5_2024.nc", "/data/era5_ref98.nc")
    time_dim = data_var["valid_time"]

    factory = EventletFactory(data_var, threshold=30 + 273.15, ref_data=ref_data)
    downstream = EventletClusterer(
        dist_threshold=1.75,
        factory_ref=factory,
        time_threshold=timedelta(days=1),
        output_path="/data/output/",
    )

    eventlet_queue = queue.Queue(maxsize=500)

    # Launch downstream thread
    downstream_thread = threading.Thread(
        target=downstream_worker, args=(eventlet_queue, downstream), daemon=True
    )
    downstream_thread.start()

    print("Processing slices...")

    for i in range(time_dim.size):
        time_val = pd.to_datetime(time_dim[i].values)

        factory.process_slice(time_val)
        for ev in factory.yield_completed():
            eventlet_queue.put(ev)

    print("All slices processed. Waiting for downstream to finish...")

    # Tell downstream to shut down after queue is empty
    eventlet_queue.put(None)
    downstream_thread.join()
    print("All done.")

    # for i in range(len(time_dim)):
    #     time_val = pd.to_datetime(time_dim[i].values)
    #     slice_data = data_var.isel(valid_time=i).load()
    #     # print(f"Loaded slice for time {time_val}")

    #     factory.process_slice(time_val, slice_data)
    #     # print(f"Processed slice {time_val}")

    #     for ev in factory.yield_completed():
    #         downstream.process_eventlet(ev)


if __name__ == "__main__":
    import pandas as pd

    main()
