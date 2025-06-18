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


def hot_pixel_distance_matrix(data, ref):
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
            metadata.append(([t], [[(lat[i_lat], lon[i_lon])]]))
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
                for dlat in [-2, -1, 0, 1, 2]:
                    for dlon in [-2, -1, 0, 1, 2]:
                        j_lat = i_lat + dlat
                        j_lon = (i_lon + dlon) % lon_len  # wrap around

                        if j_lat < 0 or j_lat >= lat_len:
                            continue
                        if dt == 0 and dlat == 0 and dlon == 0:
                            continue

                        # This is where we decide if the point is part of the same event or not
                        if mask_3d[tt, j_lat, j_lon]:
                            j_idx = ensure_metadata(tt, j_lat, j_lon)
                            p1idx.append(i_idx)
                            p2idx.append(j_idx)
                            matched_points += 1

    dists = [1] * len(p1idx)
    D = coo_matrix((dists, (p1idx, p2idx)), shape=(len(metadata), len(metadata)))
    D = D + D.T  # ensure symmetry

    return D, metadata

def min_spatial_dist(ts1, slices1, ts2, slices2):
    tset1 = set(ts1)
    tset2 = set(ts2)
    common = sorted(tset1 & tset2)
    if not common:
        return np.inf
    idx1 = {t: i for i, t in enumerate(ts1)}
    idx2 = {t: i for i, t in enumerate(ts2)}
    min_dist = np.inf
    for t in common:
        sl1 = slices1[idx1[t]]
        sl2 = slices2[idx2[t]]
        for lat1, lon1 in sl1:
            for lat2, lon2 in sl2:
                d = haversine(lat1, lon1, lat2, lon2)
                min_dist = min(min_dist, d)
    return min_dist

def extract_events_from_mask(data, ref, structure=None):
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

    mask = (data > TEMP_THRESHOLD) & (data > ref)

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
        ])
    
    print("Looking for features")
    labels, num_features = label(mask, structure=structure)
    label_slices = find_objects(labels)

    print(f"Found {num_features} features in the mask.")
    events = []

    for label_id, slc in enumerate(label_slices, start=1):
        if slc is None:
            continue

        sub_labels = labels[slc]
        coords = np.argwhere(sub_labels == label_id)
        if len(coords) < 20:
            # print(f"Skipping feature {label_id} with only {len(coords)} coordinates.")
            continue

        # Shift local coords back to global
        offsets = np.array([s.start for s in slc])
        coords += offsets  # global (t, lat, lon)

        time_to_slices = defaultdict(list)

        for t_idx, lat_idx, lon_idx in coords:
            lat = lats[lat_idx]
            lon = lons[lon_idx]
            time_to_slices[t_idx].append((lat, lon))

        all_times = sorted(time_to_slices)
        if len(all_times) < 3:
            # print(f"Skipping feature with only {len(all_times)} time points. (total {len(coords)})")
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
        slices1 = eventlets[i]["regions"]
        ts1 = eventlets[i]["times"]
        metadata.append((ts1, slices1))

        for j in range(i + 1, n):
            slices2 = eventlets[j]["regions"]
            ts2 = eventlets[j]["times"]

            # print(f"Finding dist between \n{ts1}: {slices1} and\n{ts2}: {slices2}\n\n")

            dist = min_spatial_dist(ts1, slices1, ts2, slices2)
            if dist < np.inf:
                p1.append(i)
                p2.append(j)
                dists.append(dist)

    print(
        f"Computed distances for {n} eventlets, found {len(dists)}, {sorted(dists)[:100]}..."
    )

    D = coo_matrix((dists + dists, (p1 + p2, p2 + p1)), shape=(n, n))
    return D, metadata


def find_events(data, ref, tight=False, eventlets_eps=100, features_eps=500):
    events = []
    features = []
    # D, metadata = hot_pixel_distance_matrix(data, ref)
    # db = DBSCAN(eps=1.5, min_samples=30, metric="precomputed")
    # labels = db.fit_predict(D)
    
    # eventlets = events_from_clusters(labels, metadata, 0)

    if tight:
        structure = np.array([
            [[0, 0, 0],
             [0, 1, 0],
             [0, 0, 0]],
            [[0, 1, 0],
             [1, 1, 1],
             [0, 1, 0]],
            [[0, 0, 0],
             [0, 1, 0],
             [0, 0, 0]]
        ])
    else:
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
        ])
    structure = np.array([
        [[0, 0, 0],
         [0, 1, 0],
         [0, 0, 0]],
        [[0, 1, 0],
         [1, 1, 1],
         [0, 1, 0]],
        [[0, 0, 0],
         [0, 1, 0],
         [0, 0, 0]]
    ])
    eventlets = extract_events_from_mask(data, ref, structure=structure)

    # print(f"DBSCAN events: {len(eventlets)}")
    print(f"scipy.laebl events: {len(eventlets)}")
    # print(f"first set of events: {eventlets[:5]}")

    E, metadata = eventlet_distance_matrix(eventlets)
    db = DBSCAN(eps=eventlets_eps, min_samples=1, metric="precomputed")
    labels = db.fit_predict(E)

    events = events_from_clusters(labels, metadata, 1)
    print(f"second set of events: {len(events)}")

    # F, metadata = eventlet_distance_matrix(events)
    # db = DBSCAN(eps=features_eps, min_samples=3, metric="precomputed")
    # labels = db.fit_predict(F)
    # features = events_from_clusters(labels, metadata, 2)
    # print(f"third set of events: {len(features)}")


    time_values = data.valid_time.values
    
    for event in events:
        # print(f"Event times: {event['times']}")
        event["times"] = [time_string(time_values[t]) for t in event["times"]]
        # event["regions"] = regions_from_slices(event["slices"])
    for feature in features:
        feature["times"] = [time_string(time_values[t]) for t in feature["times"]]
        # feature["regions"] = regions_from_slices(feature["slices"])
    for eventlet in eventlets:
        eventlet["times"] = [time_string(time_values[t]) for t in eventlet["times"]]
        # eventlet["regions"] = regions_from_slices(eventlet["slices"])


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
        
        # for t in time_to_slices:
        #     if len(time_to_slices[t]) > 1: 
        #         print(f"Event {label} at time {t} has {len(time_to_slices[t])} slices, merging them.")

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
    # print(f"Creating regions from {len(slices)} slices: {slices[:5]}...")
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
    t2m, ref = load_data("/data/era5_2024.nc", "/data/era5_ref98.nc")

    n = t2m.sizes["valid_time"]
    start = 0 # 1st May
    end =  start + 100
    t2m = t2m.isel(valid_time=slice(start, end))

    # Define India bounds wi' a buffer
    lat_min = 5    # a wee bit south o’ Tamil Nadu
    lat_max = 40   # up past Kashmir
    lon_min = 65   # includes bits o’ Pakistan
    lon_max = 105  # over tae Myanmar

    # Subset spatially
    t2m = t2m.sel(
        latitude=slice(lat_max, lat_min),  # lat usually runs north tae south
        longitude=slice(lon_min, lon_max)
    )

    all_events = []
    years = 0
    for eps in [100]:#[15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 300]:
        # events, features, eventlets = find_events(
        #     t2m, ref, tight=True, eventlets_eps=eps, features_eps=eps * 5
        # )
        # with open(f"/data/output/events_all_tight_{eps}.json", "w") as f:
        #     json.dump(eventlets+events+features, f, indent=2)
        # with open(f"/data/output/eventlets_tight_{eps}.json", "w") as f:
        #     json.dump(eventlets, f, indent=2)
        # with open(f"/data/output/events_tight_{eps}.json", "w") as f:
        #     json.dump(events, f, indent=2)
        # with open(f"/data/output/features_tight_{eps}.json", "w") as f:
        #     json.dump(features, f, indent=2)

        events, features, eventlets = find_events(
            t2m, ref, tight=False, eventlets_eps=eps, features_eps=eps * 5
        )
        with open(f"/data/output/events_all_{eps}.json", "w") as f:
            json.dump(eventlets+events+features, f, indent=2)
        with open(f"/data/output/eventlets_{eps}.json", "w") as f:
            json.dump(eventlets, f, indent=2)
        with open(f"/data/output/events_{eps}.json", "w") as f:
            json.dump(events, f, indent=2)
        with open(f"/data/output/features_{eps}.json", "w") as f:
            json.dump(features, f, indent=2)
        # with open(f"/data/output/events_features_{eps}.json", "w") as f:
        #     json.dump(events + features, f, indent=2)
        # for event in events:
        #     event["startTime"] = event["startTime"].replace("2024", f"{2024-years}")
        #     event["endTime"] = event["endTime"].replace("2024", f"{2024-years}")
        #     event["eps"] = eps
        # all_events += events
        # years += 1
    # with open("/data/output/events_all.json", "w") as f:
    #     json.dump(all_events, f, indent=2)


if __name__ == "__main__":
    main()

