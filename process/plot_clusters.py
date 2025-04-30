import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import numpy as np
import xarray as xr
import json

# Load cluster metadata
with open("/data/t2m_clusters.json") as f:
    clusters = json.load(f)

    # Load data
    ds = xr.open_dataset("/data/era5_2024.nc")
    t2m = ds["t2m"]
    threshold_k = 303.15

    # Group clusters by day using time indices
    valid_times = pd.to_datetime(t2m["valid_time"].values)
    cluster_by_day = {}
    for cl in clusters:
        for t_idx in cl.get("time_indices", []):
            day_str = str(valid_times[t_idx].date())
            cluster_by_day.setdefault(day_str, []).append(cl)

    # Plot one image per day
    for t_idx, t_val in enumerate(t2m["valid_time"].values):
        day_str = str(pd.to_datetime(t_val).date())
        if day_str not in cluster_by_day:
            continue  # Skip days without clusters
        fig, ax = plt.subplots(figsize=(10, 6))
        
        temp_slice = t2m.sel(valid_time=t_val)
        im = temp_slice.plot(ax=ax, cmap="plasma", vmin=280, vmax=320, add_colorbar=True)
        ax.set_title(f"T2M with clusters – {day_str}")

        # Draw cluster boxes for this day
        for cl in cluster_by_day.get(day_str, []):
            print("drawing cluster", cl["label"], "for day", day_str)
            bbox = cl["bbox"]
            rect = patches.Rectangle(
                (bbox[1], bbox[0]),  # (lon, lat)
                bbox[3] - bbox[1],  # width
                bbox[2] - bbox[0],  # height
                linewidth=2,
                edgecolor=cl["color"],
                facecolor="none"
            )
            ax.add_patch(rect)

        plt.savefig(f"/data/output/cluster_overlay_{day_str}.png")
        plt.close()
