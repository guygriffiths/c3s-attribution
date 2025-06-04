#!/usr/bin/env python3

import xarray as xr
import numpy as np
import json
from sklearn.cluster import DBSCAN
from scipy.sparse import coo_matrix
import time

# Constants
TEMP_THRESHOLD = 28 + 273.15  # Kelvin
TIME_SCALE = np.radians(0.25)  # radians per time step - 12 hours (0.5 days) equals 0.25 degrees of lat/lon
# epsilon for DBSCAN. With a regularly spaced (i.e. equally scaled in all directions) 0.25 degree grid
# this is equivalent to a knights move away in any plane. This gives quite generous clusters, which we mitigate by upping the min_samples
EPS = np.radians(0.56)
MIN_SAMPLES = 10  # minimum samples for DBSCAN
CHUNK_SIZE = 5  # size of each chunk to process
# Make the chunks overlap by enough that no edges get missed
CHUNK_OVERLAP = 0#int(np.ceil(EPS / TIME_SCALE)) + 2
MIN_CLUSTER_SIZE = 0


def load_data(data_path, ref_path):
    ds = xr.open_mfdataset(data_path)
    ref = xr.open_dataset(ref_path)

    def shift_longitudes(da):
        da = da.assign_coords(longitude=(((da.longitude + 180) % 360) - 180))
        return da.sortby("longitude")

    return shift_longitudes(ds["t2m"]), shift_longitudes(ref["t2m"])


def generate_chunks(n_timesteps, chunk_size, overlap):
    step = chunk_size
    return [(start, min(start + chunk_size + overlap, n_timesteps))
            for start in range(0, n_timesteps, step)
            if start < n_timesteps]

def index_in_metadata(metadata, newt, lat, lon):
    idx = 0
    for (t,lt,ln) in metadata:
        if lt == lat and ln == lon and t == newt:
            return idx
        idx += 1
    return -1

import numpy as np

def extract_hot_coords(data, ref):
    lat = data.latitude.values
    lon = data.longitude.values
    n_timesteps = data.sizes["valid_time"]
    lat_len = data.sizes["latitude"]
    lon_len = data.sizes["longitude"]

    # Mark hot points
    mask_3d = (data > TEMP_THRESHOLD) & (data > ref)
    mask_3d = mask_3d.transpose("valid_time", "latitude", "longitude").values

    metadata = []
    metadata_index = {}
    p1idx = []
    p2idx = []

    def get_uid(t, i_lat, i_lon):
        return (t * lat_len + i_lat) * lon_len + i_lon

    def ensure_metadata(t, i_lat, i_lon):
        uid = get_uid(t, i_lat, i_lon)
        if uid not in metadata_index:
            metadata_index[uid] = len(metadata)
            metadata.append((t, lat[i_lat], lon[i_lon]))
        return metadata_index[uid]

    for t in range(n_timesteps):
        hot_indices = np.argwhere(mask_3d[t])
        print(f"Found {len(hot_indices)} hot points at time {t}")
        matched_points = 0

        for i_lat, i_lon in hot_indices:
            i_idx = ensure_metadata(t, i_lat, i_lon)
            for dt in range(-2, 1):  # look at current and up to 2 timesteps back
                tt = t + dt
                if tt < 0 or tt >= n_timesteps:
                    continue
                for dlat in [-1, 0, 1]:
                    for dlon in [-1, 0, 1]:
                        j_lat = i_lat + dlat
                        j_lon = (i_lon + dlon) % lon_len  # wrap around

                        if j_lat < 0 or j_lat >= lat_len:
                            continue
                        if dt == 0 and dlat == 0 and dlon == 0:
                            continue
                        if mask_3d[tt, j_lat, j_lon]:
                            j_idx = ensure_metadata(tt, j_lat, j_lon)
                            p1idx.append(i_idx)
                            p2idx.append(j_idx)
                            matched_points += 1

        print(f"Matched points in timestep {t}: {len(p1idx)} edges, {len(metadata)} unique points")

    dists = [1] * len(p1idx)
    D = coo_matrix((dists, (p1idx, p2idx)), shape=(len(metadata), len(metadata)))
    D = D + D.T  # ensure symmetry

    return D, metadata




def run_dbscan(D, eps=EPS, min_samples=MIN_SAMPLES):
    if D.size == 0:
        return np.array([])

    print(f"Running DBSCAN with eps={eps}, min_samples={min_samples} on {D.shape[0]} points")
    # clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    # Time the DBSCAN function
    t1 = time.time()
    db = DBSCAN(eps=1.5, min_samples=MIN_SAMPLES, metric='precomputed')
    labels = db.fit_predict(D)  
    t2 = time.time()
    print(f"DBSCAN took {t2 - t1:.2f} seconds")
    print(f"DBSCAN found {len(set(labels))} clusters")
    # return clustering.labels_
    return labels

def find_events(data, ref):
    '''
    Warning - last_clusters is modified in place with clusters which extend it, and new clusters are returned
    '''
    D, metadata = extract_hot_coords(data, ref)
    time_values = data.valid_time.values
    labels = run_dbscan(D)

    return extract_events_from_labels(labels, metadata, time_values)

def extract_events_from_labels(labels, metadata, time_values):
    events = []

    def time_string(t):
        return str(t.astype("M8[ms]")) + 'Z'

    if labels.size == 0:
        return events

    for label in set(labels):
        if label == -1:
            continue  # noise

        points = [m for i, m in enumerate(metadata) if labels[i] == label]
        # if len(points) < MIN_CLUSTER_SIZE:
        #     continue

        times = sorted(set(p[0] for p in points))
        if len(times) < 3:
            continue

        lats = [p[1] for p in points]
        lons = [p[2] for p in points]
        max_area = max(len([p for p in points if p[0] == t]) for t in times)
        slices = [[p for p in points if p[0] == t] for t in times]

        events.append({
            "id": f"{label}",
            "times": [time_string(time_values[i]) for i in times],
            "startTime": time_string(time_values[times[0]]),
            "endTime": time_string(time_values[times[-1]]),
            "slices": slices,
            "maxArea": max_area,
            "bbox": [
                float(np.min(lats)),
                float(np.min(lons)),
                float(np.max(lats)),
                float(np.max(lons)),
            ],
            "centroid": [float(np.mean(lats)), float(np.mean(lons))],
            "size": len(points),
        })

    return events


def bboxes_overlap(b1, b2):
    lat_overlap = b1[2] >= b2[0] and b2[2] >= b1[0]
    lon_overlap = b1[3] >= b2[1] and b2[3] >= b1[1]
    return lat_overlap and lon_overlap

def main():
    t2m, ref = load_data("/data/era5_2024.nc", "/data/era5_ref98.nc")
    events = find_events(t2m, ref)
    with open("/data/output/events_output.json", "w") as f:
        json.dump(events, f, indent=2)



    # n_timesteps = t2m.sizes["valid_time"]
    # # n_timesteps = min(240, n_timesteps)  # Limit to 100 for testing
    # # n_timesteps = min(TIMESTEPS, n_timesteps)  # Limit to TIMESTEPS for testing

    # chunk_ranges = generate_chunks(n_timesteps, CHUNK_SIZE, CHUNK_OVERLAP)
    # all_clusters = []
    # last_clusters = None
    # for idx, time_range in enumerate(chunk_ranges):
    #     # if idx < 0.85*len(chunk_ranges):
    #     #     print(f"Skipping chunk {idx + 1} of {len(chunk_ranges)}: {time_range}")
    #     #     continue
    #     print(f"Processing chunk {idx + 1} of {len(chunk_ranges)}: {time_range}")
    #     clusters = cluster_chunk(t2m, ref, time_range, time_values, last_clusters)

    #     print(f"Found {len(clusters)} clusters in chunk {idx + 1}")
    #     if last_clusters is not None:
    #         all_clusters.extend(last_clusters)
    #         with open(f"/data/output/events-partial-{idx}.json", "w") as f:
    #             json.dump(all_clusters, f, indent=2)
    #     last_clusters = clusters
    # all_clusters.extend(last_clusters)
    # print(f"Total clusters found: {len(all_clusters)}")

    # # print(f"Initial cluster count: {len(all_clusters)}")
    # # merged = merge_clusters(all_clusters)
    # # print(f"Merged cluster count: {len(merged)}")



    # with open("/data/output/events_output.json", "w") as f:
    #     json.dump(all_clusters, f, indent=2)

if __name__ == "__main__":
    main()
