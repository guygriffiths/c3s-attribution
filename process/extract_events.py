#!/usr/bin/env python3

import xarray as xr
import numpy as np
import json
from sklearn.cluster import DBSCAN
from scipy.sparse import coo_matrix
from collections import defaultdict
from shapely.geometry import MultiPoint
import alphashape
# from scipy.spatial.qhull import Qh  ullError
from scipy.spatial import QhullError
# Constants
TEMP_THRESHOLD = 28 + 273.15  # Kelvin
MIN_SAMPLES = 100 # minimum samples for DBSCAN


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

def haversine(lat1, lon1, lat2, lon2):
    """Haversine distance in degrees to km."""
    R = 6371.0  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def eventlet_distance_matrix(eventlets, time_factor=100):
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
        lat1, lon1 = eventlets[i]["centroid"]
        slices = eventlets[i]["slices"]
        ts1 = eventlets[i]["times"]
        mean_radius1 = eventlets[i]["meanRadius"]
        metadata.append((ts1, lat1, lon1, slices))

        for j in range(i + 1, n):
            lat2, lon2 = eventlets[j]["centroid"]
            ts2 = eventlets[j]["times"]
            mean_radius2 = eventlets[j]["meanRadius"]

            # TODO could compare every pair of slices co-ordinates, but this is probably too slow?

            # Geographic distance
            dist = haversine(lat1, lon1, lat2, lon2)

            # Time difference based on midpoint of index ranges
            t1 = np.mean(ts1)
            t2 = np.mean(ts2)
            time_gap = abs(t1 - t2)

            # Adjust distance
            adjusted = dist - mean_radius1 - mean_radius2 + time_factor * time_gap
            if adjusted < 0:
                adjusted = 0

            p1.append(i)
            p2.append(j)
            dists.append(adjusted)

    print(f"Computed distances for {n} eventlets, found {len(dists)}, {sorted(dists)[:100]}...")

    D = coo_matrix((dists + dists, (p1 + p2, p2 + p1)), shape=(n, n))
    return D, metadata


def find_events(data, ref, eventlets_eps=100, features_eps=500):
    D, metadata = hot_pixel_distance_matrix(data, ref)
    db = DBSCAN(eps=1.5, min_samples=MIN_SAMPLES, metric='precomputed')
    labels = db.fit_predict(D)

    eventlets = []
    # Preprocess labels into groups
    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        if label != -1:
            clusters[label].append(i)

    for label, indices in clusters.items():
        n_points = len(indices)
        # if n_points < 10:
        #     continue

        cluster_data = np.array([metadata[i] for i in indices])  # shape: (n_points, 4)500
        times = cluster_data[:, 0].astype(int)
        lats = cluster_data[:, 1].astype(float)
        lons = cluster_data[:, 2].astype(float)

        centroid_lat = np.mean(lats)
        centroid_lon = np.mean(lons)
        centroid = [float(centroid_lat), float(centroid_lon)]

        # Vectorised distance calc for mean radius
        mean_rad = np.mean(np.sqrt((lats - centroid_lat) ** 2 + (lons - centroid_lon) ** 2))

        eventlets.append({
            "id": f"{label}",
            "centroid": centroid,
            "size": n_points,
            "times": sorted(set(times.tolist())),
            "meanRadius": mean_rad,
            "slices": [[(lons[i], lats[i]) for i in range(n_points) if times[i] == t] for t in sorted(set(times))],
            "bbox": [
                float(np.min(lats)),
                float(np.min(lons)),
                float(np.max(lats)),
                float(np.max(lons)),
            ],
        })

        # print(f"Found {n_points} points in cluster {label}")
    print(f"Found {len(eventlets)} eventlets with {eventlets_eps} eps")
    E, metadata = eventlet_distance_matrix(eventlets)
    db = DBSCAN(eps=eventlets_eps, min_samples=1, metric='precomputed')
    labels = db.fit_predict(E)

    time_values = data.valid_time.values
    events = extract_events_from_labels(labels, metadata, time_values)

    F, metadata = eventlet_distance_matrix(events, time_factor=250)
    db = DBSCAN(eps=features_eps, min_samples=3, metric='precomputed')
    labels = db.fit_predict(F)
    features = extract_events_from_labels(labels, metadata, time_values, feature=True)

    return events+features

def extract_events_from_labels(labels, metadata, time_values, feature=False):
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
        # print(f"Processing event {label} made up of {len(points)} eventlets")# points: {points[:5]}...")


        times = sorted(set(t for p in points for t in p[0]))
        if len(times) < 3:
            continue
        # print(f"Event {label} has {points} and times {times}")

        lats = [p[1] for p in points]
        lons = [p[2] for p in points]
        centroid = [float(np.mean(lats)), float(np.mean(lons))]
        slices = [s for p in points for t, s in zip(p[0], p[3]) if t in times]
        
        max_area = max(len(s) for s in slices)

        regions = regions_from_slices(slices)

        events.append({
            "id": f"{label}",
            "times": [i for i in times],
            # "times": [time_string(time_values[i]) for i in times],
            # "meanRadius": float(np.mean([p[3] for p in points])),
            "startTime": time_string(time_values[times[0]]),
            "endTime": time_string(time_values[times[-1]]),
            "slices": slices,
            "meanRadius": float(np.mean([np.sqrt((lat - centroid[0]) ** 2 + (lon - centroid[1]) ** 2) for lat, lon in zip(lats, lons)])),
            "regions": regions,
            "maxArea": max_area,
            "bbox": [
                float(np.min(lats)),
                float(np.min(lons)),
                float(np.max(lats)),
                float(np.max(lons)),
            ],
            "centroid": [float(np.mean(lats)), float(np.mean(lons))],
            "size": len(points),
            "feature": feature,
        })

    return events

def regions_from_slices(slices):
    # print(f"Creating regions from {len(slices)} slices: {slices[:5]}...")
    return [make_bounding_polygon(slice) for slice in slices]


def make_bounding_polygon(slice, concave=True, alpha=1.0):
    """
    Create a bounding polygon for a list of (lat, lon) coordinates.

    Args:
        slice: list of (lat, lon) tuples
        concave: whether to use concave hull (via alphashape) or convex hull
        alpha: alpha parameter for alphashape (lower = more concave)

    Returns:
        List of [lon, lat] coords forming the polygon (GeoJSON format)
    """
    # print(f"Creating bounding polygon for slice with {len(slice)} points: {slice[:5]}...")
    if len(slice) == 1:
        lat = slice[0][0]
        lon = slice[0][1]
        d_lon = 0.125
        d_lat = 0.125
        # print("Not enough points to form a polygon, returning slice as is.")
        return [[lon - d_lon, lat - d_lat],
                [lon + d_lon, lat - d_lat],
                [lon + d_lon, lat + d_lat],
                [lon - d_lon, lat + d_lat],
                [lon - d_lon, lat - d_lat]]
    elif len(slice) == 2:
        lat1, lon1 = slice[0]
        lat2, lon2 = slice[1]
        d_lon = 0.125
        d_lat = 0.125
        # print("Only two points, returning rectangle around them.")
        return [[lon1 - d_lon, lat1 - d_lat],
                [lon2 + d_lon, lat1 - d_lat],
                [lon2 + d_lon, lat2 + d_lat],
                [lon1 - d_lon, lat2 + d_lat],
                [lon1 - d_lon, lat1 - d_lat]]

    points = [(lon, lat) for lat, lon in slice]

    if concave:
        try:
            shape = alphashape.alphashape(points, alpha)
            if shape.geom_type == 'Polygon':
                return [[x, y] for x, y in np.array(shape.exterior.coords)]
            else:
                # In rare edge cases alphashape returns MultiPolygon
                largest = max(shape.geoms, key=lambda g: g.area)
                return [[x, y] for x, y in np.array(largest.exterior.coords)]
        except (QhullError, ValueError):
            # We have a non-2d value - i.e. all points are collinear
            return [[lon, lat] for lon, lat in points]  # fallback to original points
        except Exception as e:
            print(f"alphashape failed, falling back to convex: {e}")

    shape = MultiPoint(points).convex_hull
    if shape.geom_type == "Polygon":
        return [[x, y] for x, y in shape.exterior.coords]
    else:
        # still not a polygon, last resort: return all points as-is, maybe duplicate first
        print(f"Still nae polygon: {shape.geom_type}. Returning degenerate closed line.")
        coords = list(shape.coords)
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        return [[x, y] for x, y in coords]



def bboxes_overlap(b1, b2):
    lat_overlap = b1[2] >= b2[0] and b2[2] >= b1[0]
    lon_overlap = b1[3] >= b2[1] and b2[3] >= b1[1]
    return lat_overlap and lon_overlap

def main():
    t2m, ref = load_data("/data/era5_2024.nc", "/data/era5_ref98.nc")

    # n = t2m.sizes["valid_time"]
    # start = n // 3
    # end =  start + 120
    # t2m = t2m.isel(valid_time=slice(start, end))

    all_events = []
    years = 0
    for eps in range(500, 1000, 100): #[40, 50, 60, 70, 80, 90, 100, 150, 200, 300]:
        events = find_events(t2m, ref, eventlets_eps=eps, features_eps=eps * 5)
        with open(f"/data/output/events_features_{eps}.json", "w") as f:
            json.dump(events, f, indent=2)
        for event in events:
            event["startTime"] = event["startTime"].replace("2024", f"{2024-years}")
            event["endTime"] = event["endTime"].replace("2024", f"{2024-years}")
            event["eps"] = eps
        all_events += events
        years += 1
    with open("/data/output/events_all.json", "w") as f:
        json.dump(all_events, f, indent=2)


if __name__ == "__main__":
    main()
