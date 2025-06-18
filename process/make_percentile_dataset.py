#!/usr/bin/env python3

import xarray as xr

ds = xr.open_mfdataset("/data/era5_2*.nc", chunks={"valid_time": 100})  # adjust chunk size
t2m = ds["t2m"]

t2m_thresh = t2m.chunk({"valid_time": 100}).quantile(0.99, dim="valid_time")

t2m_thresh.compute().to_netcdf("/data/era5_ref99.nc")
