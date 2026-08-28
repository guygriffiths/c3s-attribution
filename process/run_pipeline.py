#!/usr/bin/env python3
"""
Operational entry point: fetch what each event type needs and find its events.

The three event types read almost nothing in common. Cold events come from the
daily minimum temperature, hot events from the daily maximum, and wet events
from total precipitation, so each one can be taken from the CDS request queue
all the way through to a catalogue entry without reference to the other two.
Running them as three independent pipelines rather than as three stages means
nobody waits for a download they are never going to read: cold events start
being detected while precipitation is still coming down the wire.

Each pipeline does the same three things, and each of the underlying pieces
already works out for itself what is missing:

    1. download_era5 compares the years on disk against the years that should
       exist and fetches only the gap, always re-fetching the current year
       because it grows day by day. It is only asked at all if this event
       type's newest file is more than a day old, since ERA5 does not gain
       anything in less than that and re-fetching the current year is the
       most expensive request the run makes.
    2. make_percentiles compares the climatology files on disk against the
       threshold this event type is configured with. In normal operation there
       is nothing to do, because the climatology is a fixed 1991-2020 baseline
       that does not move as new data arrives. It is checked anyway so that a
       fresh deployment builds what it needs from the years just fetched,
       instead of failing in detection with a missing file.
    3. find_events processes the time slices it has not already seen, resuming
       from the state this event type pickled at the end of the last run.

What the first two ask for is derived from the detection parameters rather
than listed again here, so changing a threshold or adding an event type cannot
leave a pipeline fetching inputs its detection does not read.

The types are started in the order they finish in, cold first and wet last, so
that the one with the most work ahead of it is first into the CDS queue.

Only one run may be in flight at a time. The pipelines share an output
directory, and detection rewrites a resume pickle and appends to the year
catalogues, so a run that overlaps its successor would corrupt both. A second
invocation exits immediately rather than waiting, because for a daily job the
next scheduled run is a better time to try again than the tail of the one that
is already late.

Environment:
    EVENT_INPUT_DIR:  where ERA5 data lives (default: /data)
    EVENT_OUTPUT_DIR: where events are written (default: /output)
    EVENT_MAX_WORKERS: how many event types to run at once (default: all)
    EVENT_SKIP_DOWNLOAD: set to use the data already on disk, for
        reprocessing without touching the CDS API
"""

import fcntl
import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path

from download_era5 import download_all_latest, download_land_sea_mask
from make_percentiles import PRECIP_PERCENTILES, calculate_all_percentiles
from find_events import get_default_params, process_parameter_set

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - pipeline - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)

# Nothing to retry and nothing wrong, so distinguish "a run was already going"
# from a genuine failure. 75 is EX_TEMPFAIL, which schedulers treat as such.
EX_ALREADY_RUNNING = 75

# Event types in the order they are started, which is roughly the order they
# finish in. The first one submitted is the first to reach the CDS queue, so
# the longest job should lead.
PIPELINE_ORDER = ('cold', 'hot', 'wet')

# Total CDS requests the whole run may have in flight, shared out between the
# pipelines. Each one would otherwise open its own poolful and together they
# would sail past the per-user limit, which is typically twenty.
CDS_REQUEST_BUDGET = 12

# How stale what is on disk has to be before a pipeline goes back to the CDS
# API. ERA5 gains a day at a time, so a run started within a day of the last
# successful one would queue requests for slices that cannot have moved, and
# the current year is always re-fetched, so it would be the largest of them.
MAX_DATA_AGE = timedelta(hours=24)


def take_run_lock(path):
    """
    Take the exclusive lock for this pipeline, without waiting.

    Args:
        path: Lock file, created if absent

    Returns:
        The open file descriptor holding the lock, or None if another run has
        it. The descriptor is deliberately leaked for the life of the process:
        the lock is released when it exits, however it exits.
    """
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def count_failures(results):
    """
    Total the failures reported by a download or percentile call.

    Both report a mapping of what they were asked for to a success and a
    failed list, except for the land-sea mask, which is a plain boolean.

    Args:
        results: The dictionary returned by the call

    Returns:
        Number of individual items that failed
    """
    failed = 0
    for value in results.values():
        if isinstance(value, bool):
            failed += 0 if value else 1
        else:
            failed += len(value.get('failed', []))
    return failed


def data_age(param, input_dir):
    """
    How long ago the newest file this event type reads was written.

    Only this event type's own directory is looked at, for the same reason
    the download is split up: cold data arriving says nothing about whether
    the precipitation a wet run needs is up to date.

    Args:
        param: The detection parameter set
        input_dir: Where the ERA5 data lives

    Returns:
        Time since the most recently written file, or None if this event type
        has no data at all, which is the case on a fresh deployment.
    """
    if param.event_mode == 'wet':
        data_dir = Path(input_dir) / 'precip'
    else:
        data_dir = Path(input_dir) / 't2m' / param.stat

    mtimes = [path.stat().st_mtime for path in data_dir.glob('*.nc')]
    if not mtimes:
        return None
    return timedelta(seconds=max(0.0, time.time() - max(mtimes)))


def download_for(param, input_dir, max_workers):
    """
    Fetch the ERA5 data this event type reads, and nothing else.

    The land-sea mask is deliberately not included: it is shared by all three
    pipelines, so it is fetched once before they start rather than raced for.

    Args:
        param: The detection parameter set
        input_dir: Where the ERA5 data lives
        max_workers: Concurrent CDS requests this pipeline may have in flight

    Returns:
        Number of failed downloads
    """
    if param.event_mode == 'wet':
        statistics, precip = [], True
    else:
        statistics, precip = [param.stat], False

    return count_failures(download_all_latest(
        output_dir=input_dir,
        statistics=statistics,
        include_precip=precip,
        include_land_sea_mask=False,
        max_workers=max_workers,
    ))


def percentiles_for(param, input_dir):
    """
    Build the climatology this event type reads, if it is not already there.

    Only this event type's statistic is asked for, which also avoids the trap
    in the underlying call of applying one list of temperature percentiles
    across every statistic it is given: asking for min and max together at
    both 2 and 98 would produce a cold threshold for the hot dataset and a hot
    one for the cold dataset.

    Args:
        param: The detection parameter set
        input_dir: Where the ERA5 data lives

    Returns:
        Number of failed calculations
    """
    output_dir = f"{input_dir}/climatology"
    threshold = float(param.perc) / 100.0

    if param.event_mode == 'wet':
        # The quartiles normalise the anomaly rather than threshold it, so
        # they are needed as well but are not named in the parameter set.
        percentiles = sorted(set(PRECIP_PERCENTILES) | {threshold})
        logger.info(f"Checking climatology: tp at {percentiles}")
        results = calculate_all_percentiles(
            input_dir=input_dir,
            output_dir=output_dir,
            statistics=['tp'],
            precip_percentiles=percentiles,
        )
    else:
        logger.info(f"Checking climatology: {param.stat} at {threshold}")
        results = calculate_all_percentiles(
            input_dir=input_dir,
            output_dir=output_dir,
            statistics=[param.stat],
            temp_percentiles=[threshold],
        )
    return count_failures(results)


def run_event_type(param, input_dir, output_dir, max_workers, skip_download):
    """
    Take one event type from missing data all the way to detected events.

    This runs in its own process, so nothing here is shared with the other
    event types beyond the files they each write under their own names.

    Args:
        param: The detection parameter set
        input_dir: Where the ERA5 data lives
        output_dir: Where events are written
        max_workers: Concurrent CDS requests this pipeline may have in flight
        skip_download: Use whatever is already on disk

    Returns:
        True if events were detected, False if any part of it failed
    """
    # Say which pipeline every line came from, since three of them are
    # writing to the same stream at once.
    for handler in logger.handlers:
        handler.setFormatter(logging.Formatter(
            f'%(asctime)s - {param.event_mode} - %(levelname)s - %(message)s'
        ))

    age = data_age(param, input_dir)
    if skip_download:
        logger.info("EVENT_SKIP_DOWNLOAD set, using the data already on disk")
    elif age is not None and age < MAX_DATA_AGE:
        # Detection still runs: it resumes from its own state, so there may be
        # slices left to process even when nothing new has been fetched.
        logger.info(
            f"Data last updated {age.total_seconds() / 3600:.1f}h ago, "
            f"under {MAX_DATA_AGE.total_seconds() / 3600:.0f}h; "
            f"nothing new to download"
        )
    else:
        failed = download_for(param, input_dir, max_workers)
        if failed:
            # Detection would otherwise run against whatever landed, and its
            # resume state would move past slices built from incomplete data,
            # so the gap would never be revisited.
            logger.error(f"{failed} download(s) failed; not detecting events")
            return False

    failed = percentiles_for(param, input_dir)
    if failed:
        logger.error(f"{failed} climatology file(s) failed; not detecting")
        return False

    return process_parameter_set(param, input_dir, output_dir)


def ordered_params():
    """
    The detection parameter sets, longest job first.

    Returns:
        List of parameter sets in the order their pipelines should start.
        Anything not named in PIPELINE_ORDER goes last, in the order it was
        defined, so adding an event type does not require touching the list.
    """
    def rank(param):
        if param.event_mode in PIPELINE_ORDER:
            return PIPELINE_ORDER.index(param.event_mode)
        return len(PIPELINE_ORDER)

    return sorted(get_default_params(), key=rank)


def main():
    """
    Run every event type's pipeline once.

    Returns:
        0 on success, 1 if any pipeline failed, 75 if another run holds the
        lock
    """
    input_dir = os.environ.get("EVENT_INPUT_DIR", "/data")
    output_dir = os.environ.get("EVENT_OUTPUT_DIR", "/output")

    os.makedirs(output_dir, exist_ok=True)
    lock = take_run_lock(f"{output_dir}/pipeline.lock")
    if lock is None:
        logger.warning(
            "Another run is still going; leaving it to finish. If this keeps "
            "happening the run is taking longer than the interval it is "
            "scheduled at."
        )
        return EX_ALREADY_RUNNING

    params = ordered_params()
    workers = min(len(params), int(
        os.environ.get("EVENT_MAX_WORKERS", len(params))
    ))
    skip_download = bool(os.environ.get("EVENT_SKIP_DOWNLOAD"))
    # Share the request budget between the pipelines that can be running at
    # once, rather than between all of them, so limiting concurrency does not
    # also throttle the CDS requests of the ones that are left.
    cds_workers = max(1, CDS_REQUEST_BUDGET // workers)

    logger.info("=" * 60)
    logger.info("C3S Extreme Events Pipeline")
    logger.info("=" * 60)
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(
        f"Starting {[p.event_mode for p in params]}, "
        f"{workers} at a time, {cds_workers} CDS requests each"
    )

    if not skip_download:
        # Every pipeline classifies its events against this, and they would
        # otherwise all find it missing at the same moment and download it on
        # top of each other. Detection opens it unconditionally, so there is
        # nothing to be gained by starting without it.
        if not download_land_sea_mask(input_dir):
            logger.error("Could not get the land-sea mask; detection needs it")
            return 1

    results = {}
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                run_event_type, param, input_dir, output_dir,
                cds_workers, skip_download,
            ): param
            for param in params
        }
        for future in as_completed(futures):
            param = futures[future]
            try:
                succeeded = future.result()
            except Exception as e:
                logger.error(
                    f"{param.event_mode} pipeline raised an exception: {e}",
                    exc_info=True,
                )
                succeeded = False
            results[param.event_mode] = succeeded
            logger.info(
                f"{param.event_mode.capitalize()} events finished: "
                f"{'SUCCESS' if succeeded else 'FAILED'}"
            )

    logger.info("=" * 60)
    logger.info("Run summary")
    logger.info("=" * 60)
    for event_type, succeeded in results.items():
        logger.info(
            f"{event_type.capitalize()} events: "
            f"{'SUCCESS' if succeeded else 'FAILED'}"
        )

    if all(results.values()):
        logger.info("All event types completed successfully")
        return 0

    logger.error("Some event types failed")
    return 1


if __name__ == "__main__":
    exit(main())
