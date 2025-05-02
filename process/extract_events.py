#!/usr/bin/env python3

import xarray as xr
import numpy as np
import json
from sklearn.cluster import DBSCAN

# Constants
TEMP_THRESHOLD = 28 + 273.15  # Kelvin
TIME_SCALE = np.radians(0.1)  # radians per time step
EPS = np.radians(0.38)  # epsilon for DBSCAN
MIN_SAMPLES = 30  # minimum samples for DBSCAN
TIMESTEPS = 366
CHUNK_SIZE = 10
# Make the chunks overlap by enough that no edges get missed
CHUNK_OVERLAP = int(np.ceil(EPS / TIME_SCALE))
MIN_CLUSTER_SIZE = 500

def to_radians(degrees):
    return degrees * np.pi / 180.0

def load_data(data_path, ref_path):
    ds = xr.open_dataset(data_path)
    ref = xr.open_dataset(ref_path)
    return ds["t2m"], ref["t2m"]

def generate_chunks(n_timesteps, chunk_size, overlap):
    step = chunk_size
    return [(start, min(start + chunk_size + overlap, n_timesteps))
            for start in range(0, n_timesteps, step)
            if start < n_timesteps]

def extract_hot_coords(data, ref, time_idx_range, time_values):
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

    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    return clustering.labels_

def cluster_chunk(data, ref, time_idx_range, time_values, last_clusters=None):
    coords, metadata = extract_hot_coords(data, ref, time_idx_range, time_values)
    labels = run_dbscan(coords)

    clusters = []
    if labels.size == 0:
        return clusters

    for label in set(labels):
        if label == -1:
            continue  # noise

        points = [m for i, m in enumerate(metadata) if labels[i] == label]
        if len(points) < MIN_CLUSTER_SIZE:
            continue
        times = sorted(set([p[0] for p in points]))
        lats = [p[1] for p in points]
        lons = [p[2] for p in points]
        sizes = [len([p for p in points if p[0] == t]) for t in times]

        extended = False
        if last_clusters:
            for cluster in last_clusters:
                overlap_times = set([t for t in times if t in cluster["time_indices"]])
                cdist = np.linalg.norm(
                    np.array(cluster["centroid"]) - np.array([float(np.mean(lats)), float(np.mean(lons))])
                )
                if overlap_times and bboxes_overlap(cluster["bbox"], [
                    float(np.min(lats)),
                    float(np.min(lons)),
                    float(np.max(lats)),
                    float(np.max(lons)),
                ]) and cdist < 2.0:
                    #
                    #
                    # TODO
                    #
                    #
                    # Do this better! Make sure the created cluster is good, and add it to the new list of clisters, take it out the of the old list
                    #
                    #

                    # print(f"Cluster {times}, {sizes} is similar to previous cluster {cluster}. Merging.")
                    print(f"Similar clusters, centroid distance: {cdist}")
                    # print(f"Last centroid: {cluster['centroid']}, new centroid: {[float(np.mean(lats)), float(np.mean(lons))]}")
                    # print(f"Last {CHUNK_OVERLAP} times: {cluster['time_indices'][-CHUNK_OVERLAP:]}, new times: {times[:CHUNK_OVERLAP]}")
                    # print(f"Last {CHUNK_OVERLAP} sizes: {cluster['sizes'][-CHUNK_OVERLAP:]}, new sizes: {sizes[:CHUNK_OVERLAP]}")
                    cluster["size"] += len(points)
                    cluster["time_indices"] = sorted(set(cluster["time_indices"] + times))
                    cluster["bbox"] = [
                        float(min(cluster["bbox"][0], np.min(lats))),
                        float(min(cluster["bbox"][1], np.min(lons))),
                        float(max(cluster["bbox"][2], np.max(lats))),
                        float(max(cluster["bbox"][3], np.max(lons))),
                    ]
                    cluster["sizes"].extend(sizes[CHUNK_OVERLAP:])
                    # print(f"Updated cluster {cluster} with new points.")
                    extended = True
                    break
        if not extended:
            # print(f"Creating new cluster {times}, {sizes}, centroid: {np.mean(lats)}, {np.mean(lons)}")
            clusters.append({
                "time_indices": times,
                "sizes": sizes,
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
    t2m, ref = load_data("/data/era5_2024.nc", "/data/era5_ref98.nc")
    time_values = np.array([np.datetime64(t) for t in t2m.valid_time.values])
    n_timesteps = t2m.sizes["valid_time"]
    n_timesteps = min(TIMESTEPS, n_timesteps)  # Limit to TIMESTEPS for testing

    chunk_ranges = generate_chunks(n_timesteps, CHUNK_SIZE, CHUNK_OVERLAP)
    all_clusters = []
    last_clusters = None
    for idx, time_range in enumerate(chunk_ranges):
        print(f"Processing chunk {idx + 1} of {len(chunk_ranges)}: {time_range}")
        clusters = cluster_chunk(t2m, ref, time_range, time_values, last_clusters)

        print(f"Found {len(clusters)} clusters in chunk {idx + 1}")
        if last_clusters is not None:
            all_clusters.extend(last_clusters)
        if last_clusters:
            with open(f"/data/clusters_chunk_{idx}.json", "w") as f:
                json.dump(last_clusters, f, indent=2)
        last_clusters = clusters
    all_clusters.extend(last_clusters)
    print(f"Total clusters found: {len(all_clusters)}")

    # print(f"Initial cluster count: {len(all_clusters)}")
    # merged = merge_clusters(all_clusters)
    # print(f"Merged cluster count: {len(merged)}")



    with open("/data/merged_clusters.json", "w") as f:
        json.dump(all_clusters, f, indent=2)

if __name__ == "__main__":
    main()
