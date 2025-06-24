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

def get_region(points):
    shape = MultiPoint(points).convex_hull
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
    def __init__(self, time, coords):
        self.times = [time]
        # Expecting coords as a list of (lat, lon) tuples or a NumPy array
        self.slices = [np.array(coords, dtype=np.float32)]  # list of (N, 2) arrays

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
        from shapely.geometry import MultiPoint
        return MultiPoint(target_slice).convex_hull

    def overlaps(self, coords, eps=1e-6):
        # coords: list of (lat, lon)
        test = np.array(coords, dtype=np.float32)
        current = self.slices[-1]
        for pt in test:
            if np.any(np.all(np.abs(current - pt) < eps, axis=1)):
                return True
        return False
    
    def extend(self, time, coords):
        arr = np.array(coords, dtype=np.float32)
        if time in self.times:
            idx = self.times.index(time)
            self.slices[idx] = np.vstack((self.slices[idx], arr))
        else:
            self.times.append(time)
            self.slices.append(arr)

        # Keep times + slices sorted
        sorted_pairs = sorted(zip(self.times, self.slices), key=lambda x: x[0])
        self.times, self.slices = map(list, zip(*sorted_pairs))


    def merge(self, other):
        time_to_idx = {t: i for i, t in enumerate(self.times)}

        for t, other_slice in zip(other.times, other.slices):
            if t in time_to_idx:
                i = time_to_idx[t]
                self.slices[i] = np.vstack((self.slices[i], other_slice))
            else:
                self.times.append(t)
                self.slices.append(other_slice.copy())

        # Re-sort by time
        sorted_pairs = sorted(zip(self.times, self.slices), key=lambda x: x[0])
        self.times, self.slices = map(list, zip(*sorted_pairs))

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
    def __init__(self, threshold, ref_data, expiry_days=1, min_length=3, neighbor_weight_fn=None):
        self.threshold = threshold
        self.ref_data = ref_data
        self.expiry_days = expiry_days
        self.min_length = min_length
        self.active = []
        self.output_queue = deque()
        self.neighbor_weight_fn = neighbor_weight_fn or (lambda dx, dy: 1)
        self.oldest_active_time = None
        self.id = 0

    def process_slice(self, time, data_slice):
        print(f"Processing slice at {time}")
        hot_mask = (data_slice > self.threshold) & (data_slice > self.ref_data)
        structure = np.array([[0,1,0],
                      [1,1,1],
                      [0,1,0]], dtype=bool)  # 4-connectivity
        eroded_mask = binary_erosion(hot_mask, structure=structure)
        eroded_mask = binary_erosion(eroded_mask, structure=structure)

        # print(f"Masked data")
        blobs = self._label_connected_blobs(eroded_mask)
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
            lat = np.interp(lat_idx, [lat_lo, lat_hi], [lat_vals[lat_lo], lat_vals[lat_hi]])

            lon_lo = int(np.floor(lon_idx))
            lon_hi = min(lon_lo + 1, nlon - 1)
            lon = np.interp(lon_idx, [lon_lo, lon_hi], [lon_vals[lon_lo], lon_vals[lon_hi]])

            return (float(lat), float(lon))
        
        # Convert blobs to lat/lon coordinates
        blobs = [list(map(to_latlon, blob)) for blob in blobs]

        used_blobs = set()

        for ev in self.active:
            matched = False
            for i, blob in enumerate(blobs):
                if ev.overlaps(blob):
                    ev.extend(time, blob)
                    used_blobs.add(i)
                    matched = True

            if not matched and ev.is_expired(time, self.expiry_days):
                if ev.is_valid(self.min_length):
                    self.output_queue.append(ev)
                # drop otherwise
        self.active = [ev for ev in self.active if not ev.is_expired(time, self.expiry_days)]
        # print(f"Active events after expiry check: {len(self.active)}, {self.active[0].times if self.active else 'None'}")


        
        for i, blob in enumerate(blobs):
            if i not in used_blobs:
                new_ev = Eventlet(time, blob)
                self.active.append(new_ev)
        
                # with open("/data/output/eventlets.jsonl", "a") as f:
                #     f.write(json.dumps({
                #         "id": self.id,
                #         "times": [time.isoformat()+"Z"],
                #         "coords": blob
                #     }) + "\n")
                # self.id += 1

        self.oldest_active_time = min((ev.earliest_time() for ev in self.active), default=None)

    def yield_completed(self):
        while self.output_queue:
            yield self.output_queue.popleft()

    def _label_connected_blobs(self, mask):
        # Extend mask in longitude for wrapping (assumes last axis is lon)
        extended_mask = np.concatenate([mask, mask[:, :1]], axis=1)  # add first column to end for wrapping
        structure = np.array([[0,1,0],
                            [1,1,1],
                            [0,1,0]], dtype=bool)  # 4-connectivity

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

        print(f"Found {len(blobs)} blobs in the current slice\n")
        return blobs


class EventletClusterer:
    def __init__(self, dist_threshold, factory_ref, time_threshold=timedelta(days=1), output_path="/data/output/final_events.jsonl"):
        self.dist_threshold = dist_threshold
        self.factory = factory_ref
        self.time_threshold = time_threshold
        self.eventlets = []
        self.output_path = output_path
        self.current_id = 0

    def custom_distance(self, ev1, ev2):
        ts1 = ev1.times
        ts2 = ev2.times
        idx1 = {t: i for i, t in enumerate(ts1)}
        idx2 = {t: i for i, t in enumerate(ts2)}

        min_dist = np.inf

        for t1 in ts1:
            i1 = idx1[t1]
            hull1 = ev1.hull(i1)

            for offset in [0]:#[-1, 0, 1]:
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
        print(f"Processing eventlet with {len(eventlet.times)} times\n")
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
        print(f"Finalising cluster with {len(ev.times)} times\n")
        all_times = sorted(ev.times)
        all_regions = []
        centroids = []

        all_coords = []

        for region in ev.slices:
            latlons = [(float(lat), float(lon)) for lat, lon in region]
            all_regions.append(latlons)
            all_coords.extend(latlons)

            lats, lons = zip(*latlons)
            centroid = [float(np.mean(lats)), float(np.mean(lons))]
            centroids.append(centroid)

        lats, lons = zip(*all_coords)
        bbox = [float(min(lats)), float(min(lons)), float(max(lats)), float(max(lons))]

        event_dict = {
            "id": self.current_id,
            "times": [t.isoformat()+"Z" for t in all_times],
            "regions": [get_region(region) for region in ev.slices],
            "centroids": centroids,
            "bbox": bbox
        }
        self.current_id += 1

        with open(self.output_path, "a") as f:
            f.write(json.dumps(event_dict) + "\n")




def main():
    ds = xr.open_mfdataset("/data/era5_202*.nc")
    data_var = ds["t2m"]
    print(f"Data shape: {data_var.shape}")
    time_dim = data_var["valid_time"]
    ref_data = xr.open_dataset("/data/era5_ref98.nc")["t2m"].values
    print(f"Reference data shape: {ref_data.shape}")

    factory = EventletFactory(threshold=28 + 273.15, ref_data=ref_data)
    downstream = EventletClusterer(dist_threshold=1.75, factory_ref=factory, time_threshold=timedelta(days=1), output_path="/data/output/final_events.jsonl")
    print("Processing slices...")


    for i in range(time_dim.size):
    # for i in range(121, 150):
        time_val = pd.to_datetime(time_dim[i].values)
        slice_data = data_var.isel(valid_time=i).load()

        factory.process_slice(time_val, slice_data)
        for ev in factory.yield_completed():
            downstream.process_eventlet(ev)


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
