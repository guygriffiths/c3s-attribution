#!/usr/bin/env python3

import xarray as xr
stats = ['max', 'mean']
stat = 'max'
percs = [0.98, 0.99, 0.995, 0.95]
years = range(1991,2021)
files = [f"/data/{stat}/era5_daily_{stat}_temperature_{year}.nc" for year in years]
ds = xr.open_mfdataset(files, combine="by_coords")
t2m = ds["t2m"]

for q in percs:
   t2m_thresh = t2m.quantile(q, dim="valid_time")

   t2m_thresh.compute().to_netcdf(f"/data/era5_daily_{stat}_temperature_{q*100}pc_1991-2020.nc")
