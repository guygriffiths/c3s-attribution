#!/usr/bin/env bash
shopt -s nullglob
for shp in region_fx-*.shp; do
  out="${shp%.shp}.geojson"
  ogr2ogr -f GeoJSON -lco COORDINATE_PRECISION=3 "$out" "$shp"
done