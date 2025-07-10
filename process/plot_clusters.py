#!/usr/bin/env python3

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
import xarray as xr
import json
import subprocess
import os
import numpy as np
from datetime import datetime

THRESHOLD_K = 30 + 273.15

DATA_PATH = "/data/era5_2024.nc"
REF_PATH = "/data/era5_ref99.nc"

OUTPUT_DIR = "/data/output-debug"
CLUSTER_JSON = "/data/output-debug/events.jsonl"


def load_data():
    with open(CLUSTER_JSON) as f:
        clusters = [json.loads(line) for line in f]
    ds = xr.open_mfdataset(DATA_PATH)
    t2m = ds["t2m"]
    t2m_ref = xr.open_dataset(REF_PATH)["t2m"]

    def shift_longitudes(da):
        da = da.assign_coords(longitude=(((da.longitude + 180) % 360) - 180))
        return da.sortby("longitude")

    t2m = shift_longitudes(t2m)
    t2m_ref = shift_longitudes(t2m_ref)

    return clusters, t2m, t2m_ref


def group_clusters_by_day(clusters, valid_times):
    region_by_day = {}
    slice_by_day = {}

    valid_set = set(valid_times)
    for cl in clusters:
        times = cl.get("times", [])
        regions = cl.get("regions", [])
        slices = cl.get("slices", [])

        for t_str, region, slize in zip(times, regions, slices):
            if t_str in valid_set:
                region_by_day.setdefault(t_str, []).append(region)
                slice_by_day.setdefault(t_str, []).append(slize)
    return region_by_day, slice_by_day


def plot_frame(
    ax, t2m_day, t2m_ref, regions, slices, day_str, enduring_slice=None, raw_mask=None
):
    ax.clear()

    # Background temperature (semi-transparent)
    t2m_day.plot(ax=ax, cmap="plasma", add_colorbar=False, alpha=0.2)

    # Optional: highlight enduring hot pixels (boolean mask)
    if raw_mask is not None:
        # Masked temperature, to get the colourmap
        hot_vals = t2m_day.where(raw_mask)
        hot_vals.plot(ax=ax, cmap="plasma", vmin=280, vmax=320, alpha=0.5, add_colorbar=False)
    if enduring_slice is not None:
        # Masked temperature, to get the colourmap
        hot_vals = t2m_day.where(enduring_slice)
        hot_vals.plot(ax=ax, cmap="plasma", vmin=280, vmax=320, alpha=1, add_colorbar=False)

    ax.set_title(f"T2M > threshold + clusters – {day_str}")
    cmap = plt.get_cmap("tab20")
    print(f"Plotting {len(regions)} clusters for {day_str}")

    # Cluster overlays
    for cindex, (region, slice_) in enumerate(zip(regions, slices)):
        flipped_region = [(lat, lon) for lon, lat in region]
        rect = patches.Polygon(
            flipped_region,
            linewidth=2,
            edgecolor=cmap(cindex % 20),
            facecolor="none",
        )
        ax.add_patch(rect)
        print(f"Plotting cluster {cindex} with {len(slice_)} points, {region}")

        for lon, lat in slice_:
            lon_offset = 0.02 if cindex % 4 < 2 else -0.02
            lat_offset = 0.02 if cindex % 2 == 1 else -0.02
            ax.plot(
                lat + lat_offset,
                lon + lon_offset,
                marker=".",
                color=cmap(cindex % 20),
                markersize=1,
            )



def save_frames(
    t2m, t2m_ref, region_by_day, slice_by_day, valid_times, raw_mask, enduring_pixels
):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for t_val in valid_times:
        t2m_day = t2m.sel(valid_time=np.datetime64(t_val[:-1]))
        raw_mask_slice = raw_mask.sel(valid_time=np.datetime64(t_val[:-1]))
        enduring_slice = enduring_pixels.sel(valid_time=np.datetime64(t_val[:-1]))

        fig, ax = plt.subplots(figsize=(100, 60))
        plot_frame(
            ax,
            t2m_day,
            t2m_ref,
            region_by_day.get(t_val, []),
            slice_by_day.get(t_val, []),
            t_val,
            enduring_slice,
            raw_mask_slice,
        )
        plt.savefig(f"{OUTPUT_DIR}/cluster_overlay_{t_val}.png")
        plt.close()


def create_animation(
    t2m, t2m_ref, cluster_by_day, valid_times, output="cluster_overlay.mp4"
):
    fig, ax = plt.subplots(figsize=(10, 6))

    def update(frame_idx):
        day_str = valid_times[frame_idx]
        t2m_day = t2m.sel(valid_time=np.datetime64(day_str[:-1]))
        plot_frame(ax, t2m_day, t2m_ref, cluster_by_day.get(day_str, []), day_str)

    ani = animation.FuncAnimation(fig, update, frames=len(valid_times), repeat=False)
    ani.save(f"{OUTPUT_DIR}/{output}", writer="ffmpeg", fps=5)
    print(f"Saved animation to {OUTPUT_DIR}/{output}")


def generate_video_from_frames(
    frame_dir=OUTPUT_DIR, output_file="cluster_overlay.mp4", fps=5
):
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-pattern_type",
        "glob",
        "-i",
        f"{frame_dir}/cluster_overlay_*.png",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        f"{frame_dir}/{output_file}",
    ]
    subprocess.run(cmd, check=True)
    print(f"Saved animation to {frame_dir}/{output_file}")


def main(animate=False):
    clusters, t2m, t2m_ref = load_data()

    raw_times = t2m["valid_time"].values[191:192]
    valid_times = [np.datetime_as_string(t, unit="s") + "Z" for t in raw_times]

    raw_mask = (t2m > THRESHOLD_K) & (t2m > t2m_ref)  # stays xarray

    # Rolling 3-day window to get "enduring" hot pixels
    enduring_mask = (
        raw_mask.rolling(valid_time=3, center=True)
        .sum()
        .fillna(0)
        >= 3
    )  # still DataArray, still aligned

    # Select only the days ye care about (e.g., matching valid_times)
    # enduring_mask = enduring_mask.sel(valid_time=raw_times)

    region_by_day, slice_by_day = group_clusters_by_day(clusters, valid_times)
    save_frames(
        t2m,
        t2m_ref,
        region_by_day,
        slice_by_day,
        valid_times,
        raw_mask,
        enduring_mask,
    )

    if animate:
        generate_video_from_frames()



if __name__ == "__main__":
    main()
