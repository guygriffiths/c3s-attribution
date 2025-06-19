#!/usr/bin/env python3

import xarray as xr
import numpy as np
import json
from sklearn.cluster import DBSCAN
from scipy.sparse import coo_matrix
from collections import defaultdict
from shapely.geometry import MultiPoint
import alphashape
from collections import defaultdict
from scipy.ndimage import label, find_objects

# from scipy.spatial.qhull import Qh  ullError
from scipy.spatial import QhullError

# Constants
TEMP_THRESHOLD = 28 + 273.15  # Kelvin
MIN_SAMPLES = 100  # minimum samples for DBSCAN


def load_data(data_path, ref_path):
    ds = xr.open_mfdataset(data_path)
    ref = xr.open_dataset(ref_path)

    def shift_longitudes(da):
        da = da.assign_coords(longitude=(((da.longitude + 180) % 360) - 180))
        return da.sortby("longitude")

    return shift_longitudes(ds["t2m"]), shift_longitudes(ref["t2m"])

def min_spatial_dist(ts1, slices1, ts2, slices2):
    idx1 = {t: i for i, t in enumerate(ts1)}
    idx2 = {t: i for i, t in enumerate(ts2)}

    min_dist = np.inf

    for t1 in ts1:
        i1 = idx1[t1]
        sl1 = slices1[i1]

        for offset in [0]:#[-1, 0, 1]:
            t2 = t1 + offset
            i2 = idx2.get(t2)
            if i2 is None:
                continue

            sl2 = slices2[i2]

            # Skip empty slices just in case
            if not sl1 or not sl2:
                continue

            hull1 = MultiPoint(sl1).convex_hull
            hull2 = MultiPoint(sl2).convex_hull

            if hull1.intersects(hull2):
                return 0.0  # Direct intersection or containment

            dist = hull1.distance(hull2)
            min_dist = min(min_dist, dist)

    return min_dist

def extract_eventlets(data, ref, structure=None, threshold=1.0):
    """
    Extracts connected spatiotemporal events from a 3D thresholded data array.

    Args:
        data: 3D xarray DataArray (time, lat, lon)
        ref: 3D xarray DataArray of same shape, for relative threshold

    Returns:
        List of event dicts with keys: 'times', 'slices', 'regions', 'featureLevel'
    """

    lats = data.latitude.values
    lons = data.longitude.values
    times = data.valid_time.values

    raw_mask = (data > TEMP_THRESHOLD) & (data > ref)
    mask = raw_mask.values.astype(float)

    if structure is None:
        structure = np.array([
            [[0, 1, 0],
             [1, 1, 1],
             [0, 1, 0]],
            [[1, 1, 1],
             [1, 1, 1],
             [1, 1, 1]],
            [[0, 1, 0],
             [1, 1, 1],
             [0, 1, 0]]
        ], dtype=float)
    print(f"Using structure:\n{structure}")

    # Accumulate neighbour weights
    from scipy.ndimage import convolve, label, find_objects
    votes = convolve(mask, structure, mode='constant', cval=0.0)

    # Threshold to keep only strongly-connected voxels
    connected = votes >= threshold  # adjust this threshold as needed

    # Use binary structure to define adjacency (nonzero = connected)
    binary_structure = (structure > 0).astype(int)

    labels, num_features = label(connected, structure=binary_structure)
    label_slices = find_objects(labels)

    events = []

    for label_id, slc in enumerate(label_slices, start=1):
        if slc is None:
            continue

        sub_labels = labels[slc]
        coords = np.argwhere(sub_labels == label_id)
        if len(coords) < 20:
            continue

        offsets = np.array([s.start for s in slc])
        coords += offsets

        time_to_slices = defaultdict(list)

        for t_idx, lat_idx, lon_idx in coords:
            lat = lats[lat_idx]
            lon = lons[lon_idx]
            time_to_slices[t_idx].append((lat, lon))

        all_times = sorted(time_to_slices)
        if len(all_times) < 3:
            continue
        all_slices = [time_to_slices[t] for t in all_times]

        events.append({
            "times": all_times,
            "slices": all_slices,
            "regions": regions_from_slices(all_slices),
            "featureLevel": 0,
        })

    return events


def eventlet_distance_matrix(eventlets):
    """
    Returns a sparse symmetric matrix of distances between eventlets, where distance
    is reduced based on the mean radius of each pair, and increased based on time dissimilarity.

    Args:
        eventlets: list of dicts, each with 'centroid' = (lat, lon), 'times' (as indices), 'slices'
        radius_factor: float, factor to subtract size from distance (in km)
        time_factor: float, km added per index step of time difference

    Returns:
        coo_matrix of distances
        metadata list of (times, lat, lon, meanRadius)
    """
    n = len(eventlets)
    p1 = []
    p2 = []
    dists = []
    metadata = []

    for i in range(n):
        slices1 = eventlets[i]["slices"]
        ts1 = eventlets[i]["times"]
        metadata.append((ts1, slices1))

        for j in range(i + 1, n):
            slices2 = eventlets[j]["slices"]
            ts2 = eventlets[j]["times"]

            # print(f"Finding dist between \n{ts1}: {slices1} and\n{ts2}: {slices2}\n\n")

            dist = min_spatial_dist(ts1, slices1, ts2, slices2)
            if dist < np.inf:
                p1.append(i)
                p2.append(j)
                dists.append(dist)

    # print(
    #     f"Computed distances for {n} eventlets, found {len(dists)}, {sorted(dists)[:100]}..."
    # )

    D = coo_matrix((dists + dists, (p1 + p2, p2 + p1)), shape=(n, n))
    return D, metadata


def find_events(data, ref, tight=True, eventlets_eps=100, features_eps=500):
    events = []
    features = []
    # D, metadata = hot_pixel_distance_matrix(data, ref)
    # db = DBSCAN(eps=1.5, min_samples=30, metric="precomputed")
    # labels = db.fit_predict(D)
    
    # eventlets = events_from_clusters(labels, metadata, 0)

    if tight:
        structure = np.array([
            [[0, 0.05, 0],
             [0.05, 0.15, 0.05],
             [0, 0.05, 0]],
            [[0.11, 0.15, 0.11],
             [0.15, 0, 0.15],
             [0.11, 0.15, 0.11]],
            [[0, 0.05, 0],
             [0.05, 0.15, 0.05],
             [0, 0.05, 0]]
        ])
    else:
        structure = np.array([
            [[1, 1, 1],
             [1, 1, 1],
             [1, 1, 1]],
            [[1, 1, 1],
             [1, 1, 1],
             [1, 1, 1]],
            [[1, 1, 1],
             [1, 1, 1],
             [1, 1, 1]]
        ])
  
    eventlets = extract_eventlets(data, ref, structure=structure, threshold=1.7)

    print(f"Convolve method events: {len(eventlets)}")

    E, metadata = eventlet_distance_matrix(eventlets)
    db = DBSCAN(eps=eventlets_eps, min_samples=1, metric="precomputed")
    labels = db.fit_predict(E)

    events = events_from_clusters(labels, metadata, 1)
    print(f"DBSCAN of convolved eventlets: {len(events)}")

    # F, metadata = eventlet_distance_matrix(events)
    # db = DBSCAN(eps=features_eps, min_samples=3, metric="precomputed")
    # labels = db.fit_predict(F)
    # features = events_from_clusters(labels, metadata, 2)
    # print(f"third set of events: {len(features)}")

    time_values = data.valid_time.values
    
    id = 0
    for event in eventlets+events+features:
        event["times"] = [time_string(time_values[t]) for t in event["times"]]
        event["id"] = id
        id += 1

    return events, features, eventlets


def events_from_clusters(labels, metadata, feature_level=1):
    events = []

    if labels.size == 0:
        return events

    for label in set(labels):
        if label == -1:
            continue  # noise

        points = [m for i, m in enumerate(metadata) if labels[i] == label]

        time_to_slices = defaultdict(list)

        for times, slices in points:
            for t, s in zip(times, slices):
                time_to_slices[t].append(s)

        # Now get sorted arrays
        all_times = sorted(time_to_slices)
        all_slices = []
        for t in all_times:
            merged = []
            for group in time_to_slices[t]:
                merged.extend(group)
            all_slices.append(merged)

        events.append({
            "times": all_times,
            "slices": all_slices,
            "regions": regions_from_slices(all_slices),
            "featureLevel": feature_level,
        })

    return events



def regions_from_slices(slices):
    return [make_bounding_polygon(slice, False) for slice in slices]


def make_bounding_polygon(slice, concave=True, alpha=0.25, max_alpha=5.0, alpha_step=0.25):
    if len(slice) == 1:
        lat, lon = slice[0]
        d_lon = 0.125
        d_lat = 0.125
        return [
            [lat - d_lat, lon - d_lon],
            [lat - d_lat, lon + d_lon],
            [lat + d_lat, lon + d_lon],
            [lat + d_lat, lon - d_lon],
            [lat - d_lat, lon - d_lon],
        ]
    elif len(slice) == 2:
        lat1, lon1 = slice[0]
        lat2, lon2 = slice[1]
        d_lon = 0.125
        d_lat = 0.125
        return [
            [lat1 - d_lat, lon1 - d_lon],
            [lat1 - d_lat, lon2 + d_lon],
            [lat2 + d_lat, lon2 + d_lon],
            [lat2 + d_lat, lon1 - d_lon],
            [lat1 - d_lat, lon1 - d_lon],
        ]

    points = [(lon, lat) for lat, lon in slice]

    if concave:
        current_alpha = alpha
        while current_alpha <= max_alpha:
            try:
                shape = alphashape.alphashape(points, current_alpha)
                if shape.geom_type == "Polygon":
                    return [[y, x] for x, y in shape.exterior.coords]
                elif shape.geom_type == "MultiPolygon":
                    print(f"alpha={current_alpha} gave MultiPolygon; trying higher alpha…")
                    current_alpha += alpha_step
                else:
                    print(f"Unexpected shape type: {shape.geom_type} at alpha={current_alpha}")
                    break  # unexpected type
            except Exception as e:
                print(f"alphashape failed at alpha={current_alpha}: {e}")
                break
        print("Failed tae get single polygon wi alphashape, fallback tae convex")

    shape = MultiPoint(points).convex_hull
    if shape.geom_type == "Polygon":
        return [[y, x] for x, y in shape.exterior.coords]
    else:
        # print(f"Still nae polygon: {shape.geom_type}. Returning padded bounding box instead.")
        minx, miny, maxx, maxy = shape.bounds
        pad = 0.125
        return [
            [miny - pad, minx - pad],
            [miny - pad, maxx + pad],
            [maxy + pad, maxx + pad],
            [maxy + pad, minx - pad],
            [miny - pad, minx - pad],
        ]



def bboxes_overlap(b1, b2):
    lat_overlap = b1[2] >= b2[0] and b2[2] >= b1[0]
    lon_overlap = b1[3] >= b2[1] and b2[3] >= b1[1]
    return lat_overlap and lon_overlap


def haversine(lat1, lon1, lat2, lon2):
    """Haversine distance in degrees to km."""
    R = 6371.0  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def time_string(t):
    return str(t.astype("M8[ms]")) + "Z"


def main():
    t2m, ref = load_data("/data/era5_2024.nc", "/data/era5_ref99.nc")

    # n = t2m.sizes["valid_time"]
    # start = 121 # 1st May
    # end =  start + 50
    # t2m = t2m.isel(valid_time=slice(start, end))

    # Define India bounds wi' a buffer
    # lat_min = 5    # a wee bit south o’ Tamil Nadu
    # lat_max = 40   # up past Kashmir
    # lon_min = 45   
    # lon_max = 125  

    # Subset spatially
    # t2m = t2m.sel(
    #     latitude=slice(lat_max, lat_min),  # lat usually runs north tae south
    #     longitude=slice(lon_min, lon_max)
    # )

    all_events = []
    years = 0
    for eps in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        events, features, eventlets = find_events(
            t2m, ref, tight=True, eventlets_eps=eps, features_eps=eps * 5
        )
        with open(f"/data/output/events_all_{eps}.json", "w") as f:
            json.dump(eventlets+events+features, f, indent=2)
        with open(f"/data/output/eventlets_{eps}.json", "w") as f:
            json.dump(eventlets, f, indent=2)
        with open(f"/data/output/events_{eps}.json", "w") as f:
            json.dump(events, f, indent=2)
        # with open(f"/data/output/features_{eps}.json", "w") as f:
        #     json.dump(features, f, indent=2)

        


if __name__ == "__main__":
    main()

