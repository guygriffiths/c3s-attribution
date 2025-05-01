#!/usr/bin/env python

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

def main():
    ds = xr.open_dataset("/data/era5_2024.nc")
    t2m_ref = xr.open_dataset("/data/era5_ref98.nc")["t2m"]
    threshold_k = 28 + 273.15
    tsteps = ds.sizes["valid_time"]

    fig, ax = plt.subplots(figsize=(10, 6))
    im = None

    def update(frame):
        nonlocal im
        ax.clear()
        t2m = ds["t2m"].isel(valid_time=frame)
        masked = t2m.where((t2m > threshold_k) & (t2m > t2m_ref))
        im = masked.plot(ax=ax, cmap="plasma", vmin=280, vmax=320, add_colorbar=False)
        ax.set_title(f"Hot areas – Step {frame+1}")

    ani = animation.FuncAnimation(fig, update, frames=tsteps, interval=200)  # 5 fps

    ani.save("/data/output/masked_t2m_animation.mp4", fps=5, dpi=150)
    plt.close()

if __name__ == "__main__":
    main()
