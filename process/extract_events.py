import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
import json


def main():
    ds = xr.open_dataset("/data/era5_2024.nc")
    ref = xr.open_dataset("/data/era5_ref.nc")
    threshold_k = 28 + 273.15

    coords = []
    t2m = ds["t2m"].isel(valid_time=0)  # first time slice
    t2m_ref = ref["t2m"]  # first time slice
    masked = t2m.where((t2m > threshold_k) & (t2m > t2m_ref))

    # Prepare coordinates of valid (hot) points
    lats, lons = np.meshgrid(masked.latitude, masked.longitude, indexing="ij")
    hot_mask = ~np.isnan(masked.values)
    coords.append(np.column_stack((lats[hot_mask], lons[hot_mask])))

    coords = np.vstack(coords)

    # Run DBSCAN
    if coords.size == 0:
        clusters = []
    else:
        clustering = DBSCAN(eps=1.0, min_samples=5).fit(coords)
        labels = clustering.labels_

        clusters = []
        for label in set(labels):
            if label == -1:
                continue  # noise
            points = coords[labels == label]
            cluster = {
                "label": int(label),
                "size": len(points),
                "centroid": [
                    float(np.mean(points[:, 0])),
                    float(np.mean(points[:, 1])),
                ],
                "bbox": [
                    float(np.min(points[:, 0])),
                    float(np.min(points[:, 1])),
                    float(np.max(points[:, 0])),
                    float(np.max(points[:, 1])),
                ],
            }
            clusters.append(cluster)

    # Write JSON
    with open("/data/t2m_clusters.json", "w") as f:
        json.dump(clusters, f, indent=2)


if __name__ == "__main__":
    main()
