#!/usr/bin/env python3

import xarray as xr
stats = ['max', 'mean']
percs = [0.98, 0.99, 0.995, 0.95]
years = range(1991,2021)
for stat in stats:
  for q in percs:
   files = [f"/data/{stat}/era5_daily_{stat}_temperature_{year}.nc" for year in years]
   ds = xr.open_mfdataset(files, combine="by_coords")
   t2m = ds["t2m"]

   t2m_thresh = t2m.quantile(q, dim="valid_time")

   t2m_thresh.compute().to_netcdf(f"/data/era5_daily_{stat}_temperature_{q*10}pc_1991-2020.nc")
