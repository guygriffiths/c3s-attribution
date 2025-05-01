#!/usr/bin/env python

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
import json
import hdbscan


cmap = plt.get_cmap('tab20')  # or 'tab10', 'Set3', etc.

def to_radians(degrees):
    """Convert degrees to radians."""
    return degrees * np.pi / 180.0

def to_degrees(radians):
    """Convert radians to degrees."""
    return radians * 180.0 / np.pi

def wrap_longitude(data_array, wrap_degrees=5):
    """Wraps `wrap_degrees` worth of longitudes from one edge to the other."""
    lon = data_array["longitude"]
    deg_per_step = abs(lon[1] - lon[0])
    steps = int(wrap_degrees / deg_per_step)

    # Roll longitude axis and concat extra columns on either side
    rolled = np.roll(data_array, shift=-steps, axis=-1)
    left = data_array.isel(longitude=slice(-steps, None))
    right = data_array.isel(longitude=slice(0, steps))
    extended = xr.concat([left, data_array, right], dim="longitude")

    return extended


# def pairing_score(knob, stub):
#     distance = dist(knob["centroid"], stub)

chunk_size = 10

def main():
    ds = xr.open_dataset("/data/era5_2024.nc")
    time_values = np.array([np.datetime64(t) for t in ds["valid_time"].values])
    t2m_ref = xr.open_dataset("/data/era5_ref98.nc")["t2m"]
    threshold_k = 28 + 273.15
    clusters = []
    tsteps = int(ds.sizes["valid_time"])
    tsteps = 20

    for i in range(tsteps):
        print(f"Processing time step {i+1} of {tsteps}")
        coords = []
        t2m = ds["t2m"].isel(valid_time=i)
        masked = wrap_longitude(t2m.where((t2m > threshold_k) & (t2m > t2m_ref)))

        lats, lons = np.meshgrid(masked.latitude, masked.longitude, indexing="ij")
        hot_mask = ~np.isnan(masked.values)

        # Stack (lat, lon) and convert to radians
        # because the HDBSCAN algorithm needs that
        coords.append(np.column_stack((
            to_radians(lats[hot_mask]),
            to_radians(lons[hot_mask])
        )))

        coords = np.vstack(coords)
        print(f"Found {coords.shape[0]} points in this timestep")

        if coords.size > 0:
            clustering = hdbscan.HDBSCAN(min_cluster_size=36).fit(coords)
            labels = clustering.labels_
            print(f"Found {len(set(labels))} potential clusters")

            # non_contiguous = 0
            # too_short = 0

            # Add this to extract the times per cluster:
            for label in set(labels):
                if label == -1:
                    continue  # noise
                points = coords[labels == label]
                lats = to_degrees(points[:, 0])
                lons = to_degrees(points[:, 1])
                
                cluster = {
                    "label": int(label),
                    "size": len(points),
                    "time_indices": [int(i)],
                    "time": str(time_values[i]),
                    "centroid": [
                        float(np.mean(lats)),
                        float(np.mean(lons)),
                    ],
                    "bbox": [
                        float(np.min(lats)),
                        float(np.min(lons)),
                        float(np.max(lats)),
                        float(np.max(lons)),
                    ],
                    "color": cmap(label % cmap.N)  # Use modulo to cycle through colors
                }
                clusters.append(cluster)
        # print(f"Rejected: too short: {too_short}; non-contiguous: {non_contiguous}, added {len(set(labels)) - too_short - non_contiguous} clusters")
        print(f"Found {len(clusters)} clusters in total so far")

    with open(f"/data/t2m_clusters.json", "w") as f:
        json.dump(clusters, f, indent=2)
        
        # Loop through our knobs and see if they fit one of the current stubs
        # for knob in knobs:
        #     best_match = None
        #     for stub in stubs:
        #         score = pairing_score(knob, stub)


if __name__ == "__main__":
    main()
