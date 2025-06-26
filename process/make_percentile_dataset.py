#!/usr/bin/env python3

import xarray as xr

ds = xr.open_mfdataset("/data/era5_[12]*.nc")
t2m = ds["t2m"]

t2m_thresh = t2m.quantile(0.98, dim="valid_time")

t2m_thresh.compute().to_netcdf("/data/era5_ref98.nc")
