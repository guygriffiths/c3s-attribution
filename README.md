# C3S Extreme Events Attribution

This repository contains the data-processing pipeline and web viewer for an ERA5-based extreme events application built for Copernicus Climate Change Service workflows.

At a high level, the project:

- downloads daily ERA5 temperature and precipitation fields
- derives climatological percentile thresholds from a 1991-2020 reference period
- detects spatiotemporally coherent hot, cold, and wet events
- publishes compact yearly catalogues plus per-event detail files
- serves those outputs to a Vue 3 viewer for interactive exploration

The repository is split into two main parts:

- [process](process): Python pipeline for data acquisition, climatology generation, and event detection
- [viewer](viewer): Vue 3 application that loads the generated catalogues and renders the map-based UI

## Repository layout

```text
.
├── process/        Python scripts for downloading ERA5 data and generating event outputs
├── viewer/         Vue 3 frontend that consumes the generated event catalogues
├── docker/         Python container build and conda environment
├── environments/   Deployment environment values used by GitHub Actions
└── values.yaml     Helm values template used during deployment
```

## What the application does

The processing side works on daily ERA5 fields at 0.25 degree resolution. It detects three event families using the defaults currently encoded in the pipeline:

- hot events: daily maximum temperature above both a 98th percentile climatology and an absolute 28 C threshold
- cold events: daily minimum temperature below both a 2nd percentile climatology and an absolute 0 C threshold
- wet events: daily precipitation above a wet-day 95th percentile threshold, normalized by the local interquartile range

The event detector groups neighbouring threshold-exceeding grid cells into clusters, tracks them across time, and writes two kinds of output:

- yearly catalogue files such as `events-hot-2024.jsonl`
- per-event detail files such as `events/event-hot....json`

While a run is still in progress, it also republishes provisional outputs for active events:

- `events-{type}-active.jsonl`
- `events-current/event-{id}.json`

The viewer loads those files lazily, builds client-side spatial and date indexes, and lets users:

- switch between hot, cold, wet, and combined views
- filter by duration, size, intensity, date, point, or region
- inspect individual events on an interactive map
- browse ongoing provisional events alongside the historical catalogue

## Data flow

```text
ERA5 download
  -> climatological percentiles
  -> event detection
  -> JSONL catalogues + per-event JSON
  -> static or remote data host
  -> Vue viewer
```

In code, that flow is primarily implemented in:

- [process/download_era5.py](process/download_era5.py)
- [process/make_percentiles.py](process/make_percentiles.py)
- [process/find_events.py](process/find_events.py)
- [viewer/src/lib/eventsDB.ts](viewer/src/lib/eventsDB.ts)

## Processing pipeline

### Prerequisites

You need:

- access to the Copernicus Climate Data Store with a valid `~/.cdsapirc`
- Docker or Podman-compatible container tooling if you want to use the supplied container setup
- enough disk space for raw ERA5 inputs, climatology files, and generated event outputs

The Python container definition lives in [docker/Dockerfile.python](docker/Dockerfile.python), with its environment in [docker/pyenv.yml](docker/pyenv.yml).

### Step 1: Download ERA5 inputs

The downloader in [process/download_era5.py](process/download_era5.py) fetches:

- daily minimum, mean, and maximum 2 m temperature
- daily total precipitation
- the ERA5 land-sea mask

By default it writes under `/data` in this structure:

```text
/data/
├── era5_land_sea_mask.nc
├── precip/
├── t2m/
│   ├── max/
│   ├── mean/
│   └── min/
└── climatology/
```

The checked-in [process/docker-compose.yml](process/docker-compose.yml) is currently wired to run `download_era5.py` inside the container and bind local directories from the original development machine. Treat those volume mounts as an example that will need local adjustment.

To use the supplied compose setup after adapting the paths:

```bash
cd process
docker compose up --build
```

If you prefer to run the script directly inside the prepared Python environment:

```bash
python process/download_era5.py
```

### Step 2: Build climatological thresholds

[process/make_percentiles.py](process/make_percentiles.py) computes threshold files from the 1991-2020 reference period.

Current defaults are:

- temperature percentiles: 0.5, 1, 2, 5, 95, 98, 99, 99.5
- precipitation wet-day percentiles: 25, 75, 95

Run:

```bash
python process/make_percentiles.py
```

Outputs are written to `/data/climatology` by default.

### Step 3: Detect events

[process/find_events.py](process/find_events.py) reads the downloaded inputs and climatology files, then processes hot, cold, and wet event types in parallel.

By default it expects:

- input directory from `EVENT_INPUT_DIR` or `/data`
- output directory from `EVENT_OUTPUT_DIR` or `/output`

Run:

```bash
python process/find_events.py
```

The default parameter sets in code are:

- cold: `stat=min`, `perc=2.0`, `thresh=0`, `nr=250`, `ms=60`
- hot: `stat=max`, `perc=98.0`, `thresh=28`, `nr=250`, `ms=60`
- wet: `stat=tp`, `perc=95.0`, `thresh=0.0`, `nr=250`, `ms=60`

The detector writes:

- `events-{type}-{year}.jsonl` yearly catalogues
- `events/event-{id}.json` full event files
- `events-{type}-active.jsonl` for in-progress events
- `events-current/event-{id}.json` for provisional event detail

## Viewer

The frontend in [viewer](viewer) is a Vite-powered Vue 3 app. It reads event data from the host specified by `X_DATA_ROOT`, which defaults to:

```text
https://extreme-events.service.compute.cci2.ecmwf.int/datasets/large/
```

For local development:

```bash
cd viewer
corepack enable
yarn install
yarn dev
```

For a production build:

```bash
cd viewer
yarn build
```

The two key viewer environment variables are:

- `X_PUBLIC_PATH`: base path baked into the built app
- `X_DATA_ROOT`: root URL for event catalogues and per-event JSON

Point `X_DATA_ROOT` at `/data/` if you want to serve generated outputs locally from the viewer's static host.

The viewer-specific implementation details are documented further in [viewer/README.md](viewer/README.md).

## Deployment

The production container for the frontend is defined in [viewer/Dockerfile](viewer/Dockerfile).

GitHub Actions workflows in [.github/workflows/build.yml](.github/workflows/build.yml) and [.github/workflows/deploy.yml](.github/workflows/deploy.yml) build the viewer image and deploy it via Helm using:

- [values.yaml](values.yaml)
- [environments/actions.env.common](environments/actions.env.common)
- environment-specific files in [environments](environments)

The current deployment setup is for the viewer application. The Python pipeline is operational tooling rather than a packaged deployment target in this repository.

## Notes and limitations

- The checked-in compose file contains machine-specific host paths and should be treated as a template.
- The downloader currently starts from the year defined in code, not from the full historical ERA5 record.
- The viewer and processing outputs are coupled by filename conventions and event schema, so if you change output formats in [process/find_events.py](process/find_events.py), you will likely need matching changes in [viewer/src/lib/eventsDB.ts](viewer/src/lib/eventsDB.ts) and related viewer code.

## Development entry points

If you are trying to understand the code quickly, these are the best starting files:

- [process/download_era5.py](process/download_era5.py): ERA5 acquisition
- [process/make_percentiles.py](process/make_percentiles.py): climatology thresholds
- [process/find_events.py](process/find_events.py): clustering, tracking, serialization
- [viewer/src/lib/eventsDB.ts](viewer/src/lib/eventsDB.ts): client-side indexing and filtering
- [viewer/src/store/eventStore.ts](viewer/src/store/eventStore.ts): viewer state and event-type modes
- [viewer/src/lib/utils.ts](viewer/src/lib/utils.ts): viewer data-root configuration and shared helpers

## Status

This README is based on the code currently in the repository. The core architecture is clear, but a few operational details are still encoded as local paths or defaults rather than being surfaced through a polished top-level interface.