#!/usr/bin/env python3

import numpy as np
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
        # coords: list of (lat, lon)
        test = np.array(coords, dtype=np.float32)
        current = self.slices[-1]
        for pt in test:
            if np.any(np.all(np.abs(current - pt) < eps, axis=1)):
                return True
        return False

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

        # Precompute spatial validity mask for 3+ consecutive hits
        sliding_sum = np.lib.stride_tricks.sliding_window_view(
            self.raw_mask, window_shape=3, axis=0
        ).sum(
            axis=0
        )  # shape (Y, X)
        self.valid_pixels = (sliding_sum >= 3).any(axis=2)  # shape (Y, X)
        # print(f"Valid pixels shape: {self.valid_pixels.shape}")

        self.times = self.data.valid_time.values  # in __init__

    def process_slice(self, time):
        # print(f"Processing slice at {time}")

        data_slice = self.data.sel(
            valid_time=time
        ).load()  # Load the slice for the given time
        # hot_mask = (data_slice > self.threshold) & (data_slice > self.ref_data)
        # eroded_mask = binary_erosion(eroded_mask, structure=structure)
        t = np.searchsorted(self.times, np.datetime64(time))

        time3_mask = self.raw_mask[t].copy()
        time3_mask = np.where(self.valid_pixels, time3_mask, 0)

        structure = np.array(
            [[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool
        )  # 4-connectivity
        eroded_mask = binary_erosion(time3_mask, structure=structure)
        eroded_mask = binary_erosion(eroded_mask, structure=structure)

        # print(f"Masked data")
        blobs = self._label_connected_blobs(eroded_mask, time)
        # print(f"Processing slice at {time}")

        lat_vals = data_slice["latitude"].values
        lon_vals = data_slice["longitude"].values
        nlat, nlon = len(lat_vals), len(lon_vals)

        def to_latlon(yx):
            y, x = yx
            lat_idx = np.clip(y, 0, nlat - 1)
            lon_idx = np.clip(x % nlon, 0, nlon - 1)

            # Linear interpolation between surrounding grid values
            lat_lo = int(np.floor(lat_idx))
            lat_hi = min(lat_lo + 1, nlat - 1)
            lat = np.interp(
                lat_idx, [lat_lo, lat_hi], [lat_vals[lat_lo], lat_vals[lat_hi]]
            )

            lon_lo = int(np.floor(lon_idx))
            lon_hi = min(lon_lo + 1, nlon - 1)
            lon = np.interp(
                lon_idx, [lon_lo, lon_hi], [lon_vals[lon_lo], lon_vals[lon_hi]]
            )

            return (float(lat), float(lon))

        # Convert blobs to lat/lon coordinates
        blobs = [list(map(to_latlon, blob)) for blob in blobs]

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

    def _label_connected_blobs(self, mask, time):
        # Extend mask in longitude for wrapping (assumes last axis is lon)
        extended_mask = np.concatenate(
            [mask, mask[:, :1]], axis=1
        )  # add first column to end for wrapping
        structure = np.array(
            [[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool
        )  # 4-connectivity

        labeled_array, num_features = label(extended_mask, structure=structure)

        # Wrap fix: if last column matches first, merge labels
        label_map = {}
        first_col = labeled_array[:, 0]
        last_col = labeled_array[:, -1]
        for i in range(first_col.shape[0]):
            if first_col[i] and last_col[i] and first_col[i] != last_col[i]:
                a, b = sorted((first_col[i], last_col[i]))
                label_map[b] = a

        # Flatten label_map to resolve transitive merges
        def resolve(label):
            while label in label_map:
                label = label_map[label]
            return label

        remap = np.vectorize(resolve)
        labeled_array = remap(labeled_array)

        # Clip back to original shape
        labeled_array = labeled_array[:, :-1]

        # Extract blobs
        blobs = []
        for label_val in np.unique(labeled_array):
            if label_val == 0:
                continue
            ys, xs = np.where(labeled_array == label_val)
            blob = list(zip(ys, xs))
            blobs.append(blob)

        print(f"Found {len(blobs)} blobs in the current slice at {time}\n")

        # with open("/data/output/debug.jsonl", "a") as f:
        #     for i, blob in enumerate(blobs):
        #         f.write(json.dumps({
        #             "id": f"{self.id:04d}",
        #             "times": [time.isoformat()+"Z"],
        #             # "coords": blob,
        #             "regions": [get_region(blob)],
        #             "centroids": [np.mean([pt[0] for pt in blob]), np.mean([pt[1] for pt in blob])],
        #         }) + "\n")
        #         self.id += 1

        return blobs


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
            f.write(json.dumps(catalogue_event) + "\n")
        with open(f"{self.output_path}/events/event-{event_id}.json", "w") as f:
            f.write(json.dumps(full_event) + "\n")


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


def stable_cluster_hash(time, centroid):
    """
    Stable integer hash based on time and centroid.
    """
    s = f"{str(time)}_{centroid[0]:.6f}_{centroid[1]:.6f}"
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:16], 16)


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
    data_var, ref_data = load_data("/data/era5_2024.nc", "/data/era5_ref99.nc")
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
