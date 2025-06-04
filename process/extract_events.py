#!/usr/bin/env python3

import xarray as xr
import numpy as np
import json
from sklearn.cluster import DBSCAN

# Constants
TEMP_THRESHOLD = 28 + 273.15  # Kelvin
TIME_SCALE = np.radians(0.25 * 0.5)  # radians per time step - 12 hours (0.5 days) equals 0.25 degrees of lat/lon


# Default parameter values for DBSCAN
EPS = np.radians(0.46)
MIN_SAMPLES = 100  # minimum samples for DBSCAN

CHUNK_SIZE = 10  # size of each chunk to process
# Make the chunks overlap by enough that no edges get missed
CHUNK_OVERLAP = int(np.ceil(EPS / TIME_SCALE)) + 2

def to_radians(degrees):
    return degrees * np.pi / 180.0

def load_data(data_path, ref_path):
    ds = xr.open_mfdataset(data_path)#, chunks={"valid_time": CHUNK_SIZE})
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

def extract_hot_coords(data, ref, time_idx_range):
    lat = data.latitude.values
    lon = data.longitude.values
    coords = []
    metadata = []

    for t in range(*time_idx_range):
        t2m_slice = data.isel(valid_time=t)
        mask = (t2m_slice > TEMP_THRESHOLD) & (t2m_slice > ref)

        if not np.any(mask):
            continue

        lat_grid, lon_grid = np.meshgrid(lat, lon, indexing="ij")
        lats = lat_grid[mask]
        lons = lon_grid[mask]

        times = np.full_like(lats, t, dtype=float)
        points = np.column_stack([
            times * TIME_SCALE,
            to_radians(lats),
            to_radians(lons),
        ])

        coords.append(points)
        metadata.extend([(t, lat_, lon_) for lat_, lon_ in zip(lats, lons)])

    if coords:
        return np.vstack(coords), metadata
    else:
        return np.empty((0, 3)), []

def run_dbscan(coords, eps=EPS, min_samples=MIN_SAMPLES):
    if coords.size == 0:
        return np.array([])

    print(f"Running DBSCAN with eps={eps}, min_samples={min_samples} on {coords.shape[0]} points")
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    print(f"DBSCAN found {len(set(clustering.labels_))} clusters")
    return clustering.labels_

def cluster_chunk(data, ref, time_idx_range, time_values, last_clusters=None, EPS=EPS, MIN_SAMPLES=MIN_SAMPLES):
    '''
    Warning - last_clusters is modified in place with clusters which extend it, and new clusters are returned
    '''
    coords, metadata = extract_hot_coords(data, ref, time_idx_range)
    labels = run_dbscan(coords, eps=EPS, min_samples=MIN_SAMPLES)

    clusters = []
    if labels.size == 0:
        return clusters

    def time_string(t):
        return str(t.astype("M8[ms]"))+'Z'

    for label in set(labels):
        if label == -1:
            continue  # noise

        points = [m for i, m in enumerate(metadata) if labels[i] == label]
        # if len(points) < MIN_CLUSTER_SIZE:
        #     continue
        times = sorted(set([p[0] for p in points]))
        lats = [p[1] for p in points]
        lons = [p[2] for p in points]
        max_area = max([len([p for p in points if p[0] == t]) for t in times])
        slices = [[p for p in points if p[0] == t] for t in times]

        extended = False
        if last_clusters:
            for cluster in last_clusters:
                overlap_times = set([t for t in times if t in cluster["times"]])
                cdist = np.linalg.norm(
                    np.array(cluster["centroid"]) - np.array([float(np.mean(lats)), float(np.mean(lons))])
                )
                if overlap_times and bboxes_overlap(cluster["bbox"], [
                    float(np.min(lats)),
                    float(np.min(lons)),
                    float(np.max(lats)),
                    float(np.max(lons)),
                ]) and cdist < 2.0:
                    # TODO - this is ok, but it could be more robust.
                    print(f"Similar clusters, centroid distance: {cdist}")

                    # We have a cluster that overlaps with the previous one
                    # Merge this one into the previous one
                    # This modifies last_clusters in places
                    cluster["size"] += len(points)
                    cluster["maxArea"] = max(max_area, cluster["maxArea"])
                    cluster["times"] = sorted(set(cluster["timeIndices"] + [time_string(time_values[i]) for i in times]))
                    cluster["startTime"] = time_string(time_values(cluster["timeIndices"][0]))
                    cluster["endTime"] = time_string(time_values(cluster["timeIndices"][-1]))
                    cluster["bbox"] = [
                        float(min(cluster["bbox"][0], np.min(lats))),
                        float(min(cluster["bbox"][1], np.min(lons))),
                        float(max(cluster["bbox"][2], np.max(lats))),
                        float(max(cluster["bbox"][3], np.max(lons))),
                    ]
                    cluster["slices"].extend(slices[CHUNK_OVERLAP:])
                    # print(f"Updated cluster {cluster} with new points.")
                    extended = True
                    break
        if not extended:
            # This cluster doesn't overlap with any previous clusters
            # Create a new one to return
            clusters.append({
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
                "size": len(points)
            })

    return clusters

def bboxes_overlap(b1, b2):
    lat_overlap = b1[2] >= b2[0] and b2[2] >= b1[0]
    lon_overlap = b1[3] >= b2[1] and b2[3] >= b1[1]
    return lat_overlap and lon_overlap

def main():
    t2m, ref = load_data("/data/era5_2024*.nc", "/data/era5_ref98.nc")
    time_values = np.array([np.datetime64(t) for t in t2m.valid_time.values])
    n_timesteps = t2m.sizes["valid_time"]
    # n_timesteps = min(240, n_timesteps)  # Limit to 100 for testing
    # n_timesteps = min(TIMESTEPS, n_timesteps)  # Limit to TIMESTEPS for testing
    for eps_deg in [0.36, 0.56, 0.73, 0.9, 1.0]:
        eps = np.radians(eps_deg)
        start = int((eps_deg - 0.06) * 100) - 10
        for i in range(start, start+30, 1):
            min_samples = i
            chunk_ranges = generate_chunks(n_timesteps, CHUNK_SIZE, CHUNK_OVERLAP)
            all_clusters = []
            last_clusters = None
            for idx, time_range in enumerate(chunk_ranges):#[int(0.33*len(chunk_ranges)):int(0.67*len(chunk_ranges))]):
                print(f"Processing chunk {idx + 1} of {len(chunk_ranges)}: {time_range}")
                clusters = cluster_chunk(t2m, ref, time_range, time_values, last_clusters, eps, min_samples)

                print(f"Found {len(clusters)} clusters in chunk {idx + 1}")
                if last_clusters is not None:
                    all_clusters.extend(last_clusters)
                if last_clusters:
                    with open(f"/data/output/clusters_chunk_{idx}.json", "w") as f:
                        json.dump(last_clusters, f, indent=2)
                last_clusters = clusters
            all_clusters.extend(last_clusters)
            print(f"Total clusters found: {len(all_clusters)}")

            # print(f"Initial cluster count: {len(all_clusters)}")
            # merged = merge_clusters(all_clusters)
            # print(f"Merged cluster count: {len(merged)}")

            with open(f"/data/output/events-{eps_deg}-{min_samples}.json", "w") as f:
                json.dump(all_clusters, f, indent=2)
            if len(all_clusters) == 0:
                print("No clusters found, skipping the rest parameter set.")
                break

if __name__ == "__main__":
    main()
