import xarray as xr

ds = xr.open_dataset("/data/era5_2024.nc", chunks={"valid_time": 100})  # adjust chunk size
t2m = ds["t2m"]

# Dask-backed 95th percentile
t2m_thresh = t2m.chunk({"valid_time": 100}).quantile(0.95, dim="valid_time")

t2m_thresh.compute().to_netcdf("/data/t2m_threshold_95.nc")
