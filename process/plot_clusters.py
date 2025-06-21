#!/usr/bin/env python3

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
import pandas as pd
import xarray as xr
import json
import subprocess
import os
from datetime import datetime

THRESHOLD_K = 28 + 273.15
OUTPUT_DIR = "/data/output"
CLUSTER_JSON = "/data/output/final_events.jsonl"
# CLUSTER_JSON = "/data/events_to_plot.json"
DATA_PATH = "/data/era5_2024.nc"
REF_PATH = "/data/era5_ref98.nc"

def load_data():
    # with open(CLUSTER_JSON) as f:
    #     clusters = json.load(f)
    with open(CLUSTER_JSON) as f:
        clusters = [json.loads(line) for line in f]
    ds = xr.open_dataset(DATA_PATH)
    t2m = ds["t2m"]
    t2m_ref = xr.open_dataset(REF_PATH)["t2m"]
    return clusters, t2m, t2m_ref


def group_clusters_by_day(clusters, valid_times):
    # Build a map from timestamp string → date string for lookup
    time_to_day = {t.isoformat(): str(t.date()) for t in valid_times}

    cluster_by_day = {}

    for cl in clusters:
        times = cl.get("times", [])
        regions = cl.get("regions", [])

        for t_str, region in zip(times, regions):
            day_str = time_to_day.get(t_str)
            if day_str is not None:
                cluster_by_day.setdefault(day_str, []).append(region)
    return cluster_by_day


def plot_frame(ax, t2m_day, t2m_ref, clusters, day_str):
    mask = (t2m_day > THRESHOLD_K) & (t2m_day > t2m_ref)
    masked = t2m_day.where(mask)

    ax.clear()
    t2m_day.plot(ax=ax, cmap="plasma", vmin=280, vmax=320, add_colorbar=False, alpha=0.5)
    masked.plot(ax=ax, cmap="plasma", vmin=280, vmax=320, add_colorbar=False)
    ax.set_title(f"T2M > threshold + clusters – {day_str}")
    # Get a categorical colormap
    cmap = plt.get_cmap("tab20")
    print(f"Plotting {len(clusters)} clusters for {day_str}")
    for cl in clusters:
        flippedcoords = [
            (lat, lon) for lat, lon in cl
        ]
        rect = patches.Polygon(
            flippedcoords,
            linewidth=2,
            edgecolor='black',#cmap(len(cl) % 20),  # Use size for color
            facecolor="none"
        )
        ax.add_patch(rect)

def save_frames(t2m, t2m_ref, cluster_by_day, valid_times):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for t_idx, t_val in enumerate(valid_times):
        day_str = str(t_val.date())
        t2m_day = t2m.sel(valid_time=t_val)

        fig, ax = plt.subplots(figsize=(25, 15))
        plot_frame(ax, t2m_day, t2m_ref, cluster_by_day.get(day_str, []), day_str)
        plt.savefig(f"{OUTPUT_DIR}/cluster_overlay_{day_str}.png")
        plt.close()

def create_animation(t2m, t2m_ref, cluster_by_day, valid_times, output="cluster_overlay.mp4"):
    fig, ax = plt.subplots(figsize=(10, 6))

    def update(frame_idx):
        day_str = str(valid_times[frame_idx].date())
        t2m_day = t2m.isel(valid_time=frame_idx)
        plot_frame(ax, t2m_day, t2m_ref, cluster_by_day.get(day_str, []), day_str)

    ani = animation.FuncAnimation(fig, update, frames=len(valid_times), repeat=False)
    ani.save(f"{OUTPUT_DIR}/{output}", writer='ffmpeg', fps=5)
    print(f"Saved animation to {OUTPUT_DIR}/{output}")

def generate_video_from_frames(frame_dir=OUTPUT_DIR, output_file="cluster_overlay.mp4", fps=5):
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(fps),
        "-pattern_type", "glob",
        "-i", f"{frame_dir}/cluster_overlay_*.png",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        f"{frame_dir}/{output_file}"
    ]
    subprocess.run(cmd, check=True)
    print(f"Saved animation to {frame_dir}/{output_file}")

def main(animate=False):
    clusters, t2m, t2m_ref = load_data()
    valid_times = pd.to_datetime(t2m["valid_time"].values)
    cluster_by_day = group_clusters_by_day(clusters, valid_times)
    save_frames(t2m, t2m_ref, cluster_by_day, valid_times)
    if animate:
        generate_video_from_frames()
    # if not animate:
    #     save_frames(t2m, t2m_ref, cluster_by_day, valid_times)
    # else:
    #     create_animation(t2m, t2m_ref, cluster_by_day, valid_times)

if __name__ == "__main__":
    main(True)
