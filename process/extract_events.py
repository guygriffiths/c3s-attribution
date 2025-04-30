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

# def pairing_score(knob, stub):
#     distance = dist(knob["centroid"], stub)

chunk_size = 10

def main():
    ds = xr.open_dataset("/data/era5_2024.nc")
    time_values = np.array([np.datetime64(t) for t in ds["valid_time"].values  ])
    ref = xr.open_dataset("/data/era5_ref98.nc")
    threshold_k = 28 + 273.15
    clusters = []

    TIME_SCALE = 0.25 * np.pi / 180.0  # Normalised time scale for clustering

    for tsteps in range(0, int(ds.sizes["valid_time"]), chunk_size):
        coords = []
        # A stub is a cluster which finishes at the end of the chunk
        stubs = []
        new_stubs = []
        # A knob is a cluster which starts at the beginning of the chunk
        # It attaches to a stub
        knobs = []

        # for i in range(ds.sizes["valid_time"]):
        for i in range(tsteps, min(tsteps + chunk_size, ds.sizes["valid_time"])):
            print(f"Processing time step {i+1} of {ds.sizes['valid_time']}")
            t2m = ds["t2m"].isel(valid_time=i)
            t2m_ref = ref["t2m"]
            masked = t2m.where((t2m > threshold_k) & (t2m > t2m_ref))

            lats, lons = np.meshgrid(masked.latitude, masked.longitude, indexing="ij")
            hot_mask = ~np.isnan(masked.values)

            # Stack (time, lat, lon) and convert lat-lon to radians
            # because the HDBSCAN algorithm needs that
            coords.append(np.column_stack((
                np.full(np.count_nonzero(hot_mask), i) *TIME_SCALE,  # time, normalised to the same kind of magnitude as lat/lon
                lats[hot_mask]* np.pi / 180.0,
                lons[hot_mask]* np.pi / 180.0
            )))


        coords = np.vstack(coords)
        print(f"Found {coords.shape[0]} points in this chunk")

        if coords.size > 0:
            clustering = hdbscan.HDBSCAN(min_cluster_size=36).fit(coords)
            labels = clustering.labels_
            print(f"Found {len(set(labels))} clusters")

            non_contiguous = 0
            too_short = 0

            # Add this to extract the times per cluster:
            for label in set(labels):
                if label == -1:
                    continue  # noise
                points = coords[labels == label]
                times = (points[:, 0] / TIME_SCALE).astype(int)  # Convert to time indices
                lats = points[:, 1] / (np.pi / 180.0)
                lons = points[:, 2] / (np.pi / 180.0)
                days = np.unique(times)
                # print(f"Found cluster with days {times}. {days} unique, contiguous: {contiguous}")

                # Filter out clusters that are too small or have a break
                if (len(days) < 3 and times[-1] != (i+chunk_size)):
                    # print(f"Skipping cluster")
                    too_short += 1
                    continue
                # Test if days are contiguous
                contiguous = np.all(np.diff(days) == 1)
                if not contiguous:
                    non_contiguous += 1
                    continue
                
                cluster = {
                    "label": int(label),
                    "size": len(points),
                    "days": len(days),
                    "time_indices": days.tolist(),
                    "times": [f"{time_values[t]}" for t in days],
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
                # For when we want to join clusters. For now don't worry about it
                # if(tsteps in days.tolist()):
                #     knobs.append(cluster)
                # elif((tsteps + chunk_size - 1) in days.tolist()):
                #     stubs.append(cluster)
                # else:
                #     clusters.append(cluster)
                clusters.append(cluster)
        print(f"Rejected: too short: {too_short}; non-contiguous: {non_contiguous}, added {len(set(labels)) - too_short - non_contiguous} clusters")
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
