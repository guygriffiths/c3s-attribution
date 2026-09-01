# Extremes ERA — Viewer

A Vue 3 single-page application for exploring extreme heat, cold, and wet events derived from ERA5 reanalysis data.

The viewer is built for fast browsing through a large event catalogue. You can move quickly from a whole-planet overview to a specific event, scrub across time, filter by space and event properties, and inspect detail without waiting for the entire archive to load up front.

## Why it feels fast

This app is tuned for exploratory browsing rather than one-shot page loads.

- It fetches the event types currently on screen first, with the most recent year first, so the opening view becomes useful before the rest of the archive arrives.
- It loads one year-file at a time in a Web Worker and builds spatial and date indexes off the main thread.
- It keeps several cached filter stages in memory, so changing a time window does not force a full rebuild of spatial and parameter filtering.
- It renders the overview heatmap on an offscreen canvas in a worker instead of doing all map drawing on the UI thread.
- It computes timeline summaries in a separate worker, so scrubbing and playback stay responsive.
- It only fetches full event geometry when you ask for a specific event; the catalogue stays compact.

In practice, that means you can start browsing recent visible data quickly, tighten filters interactively, and dive into event detail on demand.

## What you can do

- browse hot, cold, wet, and combined event modes
- move between map overview, timeline, ranked events, and event detail views
- filter by duration, size, intensity, date window, point, or named/drawn region
- inspect events in progress alongside the finished historical catalogue
- compare how event counts and footprints evolve through time
- jump from a catalogue summary to full event geometry only when needed

---

## Prerequisites

- **Node.js** ≥ 18
- **Yarn** (v4, via Corepack) — `corepack enable && corepack prepare yarn@stable --activate`

---

## Getting started

```bash
# Install dependencies
yarn install

# Start dev server (hot-reload on http://localhost:5173)
yarn dev

# Production build → dist/
yarn build
```

The build inlines a `base` path taken from `X_PUBLIC_PATH` in `.env`. Set this to `/` when serving from a custom domain, or to `/subpath/` for a GitHub Pages sub-path deployment.

---

## Data

Event data is served as JSONL files from the host given by `X_DATA_ROOT`, by default
`https://extreme-events.service.compute.cci2.ecmwf.int/datasets/large/`. Since that is a
different origin to the app, the host must send permissive CORS headers. Point
`X_DATA_ROOT` at `/data/` to serve out of `public/data/` instead.

```
events-hot-{year}.jsonl    # one file per year, extreme heat events
events-cold-{year}.jsonl   # one file per year, extreme cold events
events-wet-{year}.jsonl    # one file per year, extreme precipitation events
events-{type}-active.jsonl # events still in progress, republished every time step
regions.geojson            # named regions used for spatial filtering
events/                    # per-event detail files (loaded on demand)
events-current/            # per-event detail for the events still in progress
compare/                   # data used for comparison views
```

Each `events-{type}-{year}.jsonl` line is a JSON object describing a single event: bounding pixels, timestamps, duration, area, and intensity statistics.

The catalogue format is deliberately split for browsing speed:

- yearly JSONL files contain compact summaries that are cheap to stream and index
- detailed event geometries live in per-event JSON files and are only loaded on demand

Event data is loaded lazily. The fetch/index worker retrieves one year-file at a time, parses the JSONL off the main thread, and builds pixel and date indexes in the background. The viewer now prioritises the event types that are actually visible, so the opening mode is not blocked behind decades of hidden data.

Events that have not finished yet are carried in `events-{type}-active.jsonl` and flagged
`"provisional": true`. They are fetched once, at page load, so a site refresh is what picks
up newer ones. Both their extent and their id can still change as more data arrives, and
their detail is fetched from `events-current/` rather than `events/`.

---

## Code layout

```
src/
  main.ts                 Entry point — mounts the Vue app, registers plugins
  App.vue                 Root component; wraps Main with a loading overlay
  types.d.ts              Global TypeScript type declarations (ExtremeEvent, Filters, …)
  env.d.ts                Vite env type augmentation

  components/
    Main.vue              Top-level layout: map, panels, header controls
    Map.vue               Leaflet map wrapper; draws event polygons via canvas overlay
    TimeReel.vue          Horizontal timeline scrubber with drag handles
    FilterPanel.vue       Hamburger-menu panel for duration/size/intensity filters
    EventInfoPanel.vue    Detail panel for the currently focused event
    EventDayPanel.vue     Summary of all events active on the selected day
    SelectedEventInfoPanel.vue  Persistent side panel for a pinned event
    MultiEventSmartPanel.vue    Charts comparing multiple events or time series
    EventGraphs.vue       D3 graphs (scatter plot, histogram) for the event set
    ColorScale.vue        Legend/colour scale component
    FooterLogos.vue       Institutional logos in the footer
    AppLogo.vue           Application logo/branding mark

    util/                 Reusable UI primitives
      Histogram.vue       Generic D3 histogram
      ScatterPlot.vue     Generic D3 scatter plot
      RegionControl.vue   Map drawing controls (point / polygon selection)
      EventRanker.vue     Ranked list of top events
      EventTypeToggle.vue Heat / cold / both toggle
      ModeToggle.vue      Time-machine vs. heatmap view toggle
      HelpButton.vue      Opens contextual help overlay
      HelpOverlay.vue     Modal help overlay host
      FocusFrame.vue      Highlight frame drawn around selected events
      Loading.vue         Spinner/overlay for async states
      NumberSelect.vue    Numeric input with increment/decrement
      CalendarIcon.vue    Small SVG calendar icon

    help/                 Per-component help text rendered inside HelpOverlay
      AboutInfoHelp.vue
      EventDayPanelHelp.vue
      EventGraphsHelp.vue
      EventInfoHelp.vue
      HamburgerMenuHelp.vue
      MultiEventPanelHelp.vue
      RegionControlHelp.vue
      SelectedInfoHelp.vue
      TimeReelHelp.vue

    errors/               Error boundary / error display components

  store/
    store.ts              Main Pinia store — UI state: view mode, loading flags,
                          map centre, filter-drawing state, panel visibility
    eventStore.ts         Event Pinia store — loaded events, active filters,
                          selected/hovering event, colour scales
    timeStore.ts          Time Pinia store — current date, playback state,
                          time-window handles

  lib/
    eventsDB.ts           In-memory event database and filtering pipeline.
                          Maintains four cached filter stages:
                            all → parameter-filtered → spatially-filtered
                            → time-filtered → fully-filtered
    utils.ts              Shared utilities: DATA_ROOT path, pixel packing/
                          unpacking (matching the backend's lat/lon encoding),
                          colour interpolation, debounce, DOM helpers
    map-utils.ts          Leaflet/geometry helpers for coordinate transforms
    renderer.ts           Canvas rendering logic for event polygons on the map
    histo-utils.ts        Histogram bin calculation helpers
    time-utils.ts         Date arithmetic and formatting helpers
    eventFilters.ts       Pure filter predicate functions
    help.ts               Help content registry
    labels.ts             All user-visible strings (i18n-ready; currently English only)

    worker/               Web Workers (loaded via Vite's `?worker` import)
      fetchAndIndexWorker.ts        Fetches a year's JSONL, parses events,
                                    builds pixel/date indexes, and supports
                                    visible-types-first loading
      heatmapRenderWorker.ts        Renders the heatmap canvas layer off-thread
                                    with an OffscreenCanvas
      timeReelEventProcessWorker.ts Pre-processes event data for the TimeReel
                                    and yearly summaries off-thread

  router/
    index.ts              Vue Router config (single route; 404 redirect handled
                          by build-time copy of index.html to 404.html)

  assets/
    styles/               Global SCSS — design tokens, resets, typography
```

---

## Environment variables

All env vars must be prefixed `X_` to be exposed to the client bundle (see `vite.config.ts`).

| Variable | Default | Description |
|---|---|---|
| `X_PUBLIC_PATH` | `/` | Base path for the deployed app. Set to `/subpath/` for sub-directory deployments. |
| `X_DATA_ROOT` | `https://extreme-events.service.compute.cci2.ecmwf.int/datasets/large/` | Where event data is fetched from. Must end in a slash. Set to `/data/` to serve out of `public/data/`. |

---

## Architecture notes

**Filtering pipeline** (`lib/eventsDB.ts`): filters are applied in a four-stage chain — parameter filters (type/duration/size/intensity) → spatial filter (point or drawn region) → time filter (date window). Each stage caches its output; downstream stages are only recomputed when an upstream stage changes.

**Loading strategy** (`lib/eventsDB.ts`): the app asks for the event types currently visible first, starting from the most recent year, and only sends the rest of the workload once that foreground wave has landed. That gets the opening map and current time selection usable earlier.

**Workers**: three Web Workers keep the main thread responsive. The fetch/index worker streams event data year-by-year and builds indexes; the heatmap render worker draws the overview canvas off-thread; the time-reel worker processes visible-event lists and yearly summary shapes for the timeline.

**Pixel encoding**: events store geographic coverage as a set of packed integers (`(lat*4 << 16) | (lon*4 & 0xffff)`). The same algorithm is used in the Python backend and mirrored in `lib/utils.ts` for fast client-side spatial lookup.

**On-demand detail**: the catalogue carries enough metadata for ranking, filtering, and time browsing. The much heavier per-event geometry is fetched only when the user selects an event.

**Stores**: three Pinia stores with clear ownership — main UI state, event data/selection, and timeline/playback state. Components read from stores via composables; workers communicate back via `postMessage`.

## Performance model

If you are modifying the viewer, this is the core design to preserve:

1. Keep the catalogue summaries cheap to load and index.
2. Push parsing, indexing, and aggregate computations into workers.
3. Recompute only the lowest filter stage affected by a change.
4. Fetch full event payloads only when the user asks for them.
5. Prefer making the current visible mode fast over making every dataset load at once.
