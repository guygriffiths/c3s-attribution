from pathlib import Path
import xarray as xr
import numpy as np
import json
from scipy.ndimage import label

TEMP_THRESHOLD = 28 + 273.15  # Kelvin to Celsius conversion

def load_data(file_path):
    return xr.open_dataset(file_path)


def apply_mask(data, ref, var_name="t2m", threshold=TEMP_THRESHOLD):
    """
    Create a binary mask where data[var_name] > ref.
    Assumes matching dimensions (time, lat, lon).
    """
    return ((data[var_name] > threshold) & (data[var_name] > ref[var_name])).values


def cluster_mask(mask):
    """
    Perform connected component labeling across a 3D mask.
    Returns:
        - labeled array
        - number of clusters
    """
    # Structure defines connectivity: 6-connectivity in 3D
    struct = np.zeros((3, 3, 3), dtype=bool)
    struct[1, 1, :] = True
    struct[1, :, 1] = True
    struct[:, 1, 1] = True
    labeled, num_features = label(mask, structure=struct)
    return labeled, num_features


def clusters_to_json(labeled, num_features):
    """
    Converts labeled array into JSON serializable list of clusters.
    Each cluster is a list of [time, lat, lon] indices.
    """
    clusters = [[] for _ in range(num_features)]
    it = np.nditer(labeled, flags=["multi_index"])
    for val in it:
        if val > 0:
            clusters[val - 1].append(list(it.multi_index))
    return clusters


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def main(input_path="input.nc", ref_path="ref.nc", output_path="clusters.json"):
    data = load_data(input_path)
    ref = load_data(ref_path)
    mask = apply_mask(data, ref)
    labeled, num = cluster_mask(mask)
    clusters = clusters_to_json(labeled, num)
    save_json(clusters, output_path)


if __name__ == "__main__":
    main('/data/era5_2024.nc', '/data/era5_ref98.nc', '/data/clusters.json')