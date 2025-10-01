import json
import numpy as np
from collections import defaultdict


def load_events(path):
    with open(path, "r") as f:
        return [json.loads(line) for line in f]


def get_duration(event):
    times = event.get("times", [])
    if len(times) < 2:
        return 0
    return (
        (np.datetime64(times[-1]) - np.datetime64(times[0]))
        .astype("timedelta64[h]")
        .astype(int)
    )


def compute_percentiles(events, fields, extra_percentiles=[98, 99]):
    percentiles = list(range(5, 100, 5)) + extra_percentiles
    stats = defaultdict(dict)

    for field in fields:
        values = []
        for ev in events:
            if field == "duration":
                v = get_duration(ev)
            else:
                v = ev.get(field)
            if v is not None:
                values.append(v)

        if not values:
            continue

        values = np.array(values)
        for p in percentiles:
            stats[field][p] = float(np.percentile(values, p))

    return stats


def print_percentile_summary(stats):
    for field, ptiles in stats.items():
        print(f"\nField: {field}")
        for p in sorted(ptiles):
            print(f"  {p:2d}th percentile: {ptiles[p]:.3f}")


# --- usage ---
events = load_events("/data/output/events.jsonl")
fields = ["total_area", "peak_value", "mean_value", "duration"]
stats = compute_percentiles(events, fields)
print_percentile_summary(stats)


# Optionally compare one event:
def percentile_rank(value, field, stats):
    for p in sorted(stats[field]):
        if value < stats[field][p]:
            return f"< {p}th"
    return "≥ 99th"


# Example usage:
# event = events[0]
# for field in fields:
#     if field == "duration":
#         value = get_duration(event)
#     else:
#         value = event.get(field)
#     if value is not None:
#         print(f"{field}: {value:.2f} → {percentile_rank(value, field, stats)}")
