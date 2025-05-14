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
MIN_SAMPLES = 50  # minimum samples for DBSCAN
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

def extract_hot_coords(data, ref):
    lat = data.latitude.values
    lon = data.longitude.values
    n_timesteps = 10 #data.sizes["valid_time"]

    metadata = []
    n_lons = data.sizes["longitude"]
    points = []
    # total_counts = []
    p1idx = []
    p2idx = []
    dists = []

    # total_count = 0
    for t in range(n_timesteps):
        t2m_slice = data.isel(valid_time=t)
        mask = (t2m_slice > TEMP_THRESHOLD) & (t2m_slice > ref)

        if not np.any(mask):
            continue
        indices = np.argwhere(mask.values)
        print(f"Found {len(indices)} hot points at time {t}")
        points.append(indices)
        # print(f"points is now: {points} ({len(points)} points, {total_count} total)")
        matched_points = 0
        for i in range(len(indices)):
            # First check distance from every other point here
            i_lat, i_lon = indices[i]

            matchedI = False
            i_index = -1
            
            for j in range(i + 1, len(indices)):
                j_lat, j_lon = indices[j]

                lat_diff = abs(i_lat - j_lat)
                if lat_diff > 1:
                    continue

                lon_diff = abs(i_lon - j_lon)

                if lon_diff > n_lons / 2:
                    # Wrap around the longitudes
                    lon_diff = n_lons - lon_diff

                if lon_diff > 1:
                    continue

                # We have a match!
                matched_points += 1
                if not matchedI:
                    # Check if this point is already in the metadata
                    idx = index_in_metadata(metadata, t, lat[i_lat], lon[i_lon])
                    if idx == -1:
                        # Not in metadata, add it
                        i_index = len(metadata)
                        metadata.append((t, lat[i_lat], lon[i_lon]))
                    else:
                        # Already in metadata, use that index
                        i_index = idx
                    matchedI = True

                dist = 1 #np.sqrt((lat[i_lat] - lat[j_lat]) ** 2 + (lon[i_lon] - lon[j_lon]) ** 2)
                p1idx.append(i_index)

                p2idx.append(len(metadata))
                metadata.append((t, lat[j_lat], lon[j_lon]))

                dists.append(dist)
            for oldt in range(max(0, t-2), t):
                oldindices = points[oldt]
                for j in range(len(oldindices)):
                    j_lat, j_lon = oldindices[j]
                    # We also consider nearest neighbours in the previous time step
                    if abs(i_lat - j_lat) > 1 or abs(i_lon - j_lon) > 1:
                        continue

                    # We have a match!
                    matched_points += 1
                    idx = index_in_metadata(metadata, t, lat[i_lat], lon[i_lon])
                    if idx == -1:
                        # Not in metadata, add it
                        i_index = len(metadata)
                        metadata.append((t, lat[i_lat], lon[i_lon]))
                    else:
                        # Already in metadata, use that index
                        i_index = idx
                        

                    p1idx.append(i_index)

                    idx = index_in_metadata(metadata, oldt, lat[j_lat], lon[j_lon])
                    if idx == -1:
                        # Not in metadata, add it
                        idx = len(metadata)
                        metadata.append((oldt, lat[j_lat], lon[j_lon]))
                    p2idx.append(idx) 
                    dist = 1
                    dists.append(dist)
                    # print(f"\tNear point {j_lat}, {j_lon} in previous time step, p1idx, p2idx {p1idx[-1]} {p2idx[-1]}")
        # total_count += len(indices)
        print(f"Matched points {matched_points} in this time step {t} with {len(indices)} indices ({len(metadata)} metadata entries). len(p1idx) {len(p1idx)}")
        # total_counts.append(total_count)

        # metadata.extend([(t, lat_, lon_) for lat_, lon_ in zip([lats, lons)])

    # Combine distances into sparse matrix
    D = coo_matrix((dists, (p1idx, p2idx)), shape=(matched_points, matched_points))

    # Make it symmetric (DBSCAN expects full pairwise distances)
    D = D + D.T
    return  D, metadata

    # coords = np.vstack(coords) if coords else np.empty((0, 3))
    # metadata = np.array(metadata) if metadata else  []
    # print(f"Extracted {coords}")
    # return coords, metadata



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

def cluster_chunk(data, ref, time_idx_range, time_values, last_clusters=None):
    '''
    Warning - last_clusters is modified in place with clusters which extend it, and new clusters are returned
    '''
    coords, metadata = extract_hot_coords(data, ref)
    labels = run_dbscan(coords)

    clusters = []
    if labels.size == 0:
        return clusters

    def time_string(t):
        return str(t.astype("M8[ms]"))+'Z'

    for label in set(labels):
        if label == -1:
            continue  # noise

        points = [m for i, m in enumerate(metadata) if labels[i] == label]
        if len(points) < MIN_CLUSTER_SIZE:
            continue
        times = sorted(set([p[0] for p in points]))
        if len(times) < 3:
            continue
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
    t2m, ref = load_data("/data/era5_2024.nc", "/data/era5_ref98.nc")
    time_values = np.array([np.datetime64(t) for t in t2m.valid_time.values[:int(t2m.sizes["valid_time"]/2)]])
    clusters = cluster_chunk(t2m, ref, None, time_values, None)
    with open("/data/output/events_output.json", "w") as f:
        json.dump(clusters, f, indent=2)



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
