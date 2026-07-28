# Extremes ERA — Viewer

A Vue 3 single-page application for exploring extreme temperature events derived from ERA5 reanalysis data. Users can browse heat and cold-wave events across the historical record (1979–present), filter by duration, geographic area, or intensity, and inspect individual events on an interactive map.

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

Event data is served as JSONL files in `public/data/`:

```
public/data/
  events-hot-{year}.jsonl    # one file per year, extreme heat events
  events-cold-{year}.jsonl   # one file per year, extreme cold events
  regions.geojson             # named regions used for spatial filtering
  events/                     # per-event detail files (loaded on demand)
  compare/                    # data used for comparison views
```

Each `events-{type}-{year}.jsonl` line is a JSON object describing a single event: bounding pixels, timestamps, duration, area, and intensity statistics.

Event data is loaded lazily: the fetch/index worker retrieves one year-file at a time and builds a spatial pixel index in the background. Detailed event geometry is fetched on demand from `events/` when the user selects a specific event.

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
                                    builds a pixel→event-index map
      heatmapRenderWorker.ts        Renders the heatmap canvas layer off-thread
      timeReelEventProcessWorker.ts Pre-processes event data for the TimeReel

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

---

## Architecture notes

**Filtering pipeline** (`lib/eventsDB.ts`): filters are applied in a four-stage chain — parameter filters (type/duration/size/intensity) → spatial filter (point or drawn region) → time filter (date window). Each stage caches its output; downstream stages are only recomputed when an upstream stage changes.

**Workers**: three Web Workers keep the main thread responsive. The fetch/index worker streams event data year-by-year; the heatmap render worker draws the overview canvas off-thread; the time-reel worker processes visible-event lists for the timeline.

**Pixel encoding**: events store geographic coverage as a set of packed integers (`(lat*4 << 16) | (lon*4 & 0xffff)`). The same algorithm is used in the Python backend and mirrored in `lib/utils.ts` for fast client-side spatial lookup.

**Stores**: three Pinia stores with clear ownership — main UI state, event data/selection, and timeline/playback state. Components read from stores via composables; workers communicate back via `postMessage`.
