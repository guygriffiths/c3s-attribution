"""
Compute percentile statistics from detected extreme temperature events.

This script analyzes a catalogue of detected events (JSONL format) to calculate
percentile distributions for key event characteristics: duration, total area,
peak intensity, and mean intensity. These statistics are used to set sensible
default visualization limits and provide context for individual event severity.

The percentile thresholds help answer questions like:
- What duration makes an event "unusually long"?
- How large is a "major" event compared to typical events?
- What temperature values represent extreme intensities?

These statistics inform the UI's default filters, color scales, and event
classification thresholds.
"""

import json
import numpy as np
from collections import defaultdict


def load_events(path):
    """
    Load event catalogue from JSONL file.
    
    Args:
        path: Path to JSONL file where each line is a JSON event object
        
    Returns:
        List of event dictionaries
    """
    with open(path, "r") as f:
        return [json.loads(line) for line in f]


def get_duration(event):
    """
    Calculate event duration in hours from start to end time.
    
    Args:
        event: Event dictionary containing 'times' array
        
    Returns:
        Duration in hours, or 0 if event has fewer than 2 time points
    """
    times = event.get("times", [])
    if len(times) < 2:
        return 0
    
    return (
        (np.datetime64(times[-1]) - np.datetime64(times[0]))
        .astype("timedelta64[h]")
        .astype(int)
    )


def compute_percentiles(events, fields, extra_percentiles=[98, 99]):
    """
    Compute percentile distributions for specified event fields.
    
    Calculates percentiles at 5% intervals (5th, 10th, ..., 95th) plus
    additional high percentiles (98th, 99th) to characterize extreme events.
    
    Args:
        events: List of event dictionaries
        fields: List of field names to analyze (e.g., 'total_area', 'duration')
        extra_percentiles: Additional percentile values to compute beyond
                          the standard 5% intervals (default: [98, 99])
        
    Returns:
        Nested dictionary: {field_name: {percentile: value}}
        
    Example:
        {
            'duration': {5: 24.0, 10: 48.0, ..., 99: 720.0},
            'total_area': {5: 50000.0, 10: 75000.0, ..., 99: 2500000.0}
        }
    """
    percentiles = list(range(5, 100, 5)) + extra_percentiles
    stats = defaultdict(dict)
    
    for field in fields:
        values = []
        
        # Extract values for this field from all events
        for ev in events:
            if field == "duration":
                v = get_duration(ev)
            else:
                v = ev.get(field)
            
            if v is not None:
                values.append(v)
        
        if not values:
            continue
        
        # Compute percentiles
        values = np.array(values)
        for p in percentiles:
            stats[field][p] = float(np.percentile(values, p))
    
    return stats


def print_percentile_summary(stats):
    """
    Print formatted percentile statistics to console.
    
    Args:
        stats: Nested dictionary from compute_percentiles()
    """
    for field, ptiles in stats.items():
        print(f"\nField: {field}")
        for p in sorted(ptiles):
            print(f"  {p:2d}th percentile: {ptiles[p]:.3f}")


def percentile_rank(value, field, stats):
    """
    Determine which percentile bracket a value falls into.
    
    Args:
        value: The value to classify
        field: Which field this value represents (e.g., 'duration')
        stats: Percentile statistics from compute_percentiles()
        
    Returns:
        String describing percentile bracket (e.g., "< 50th", "≥ 99th")
        
    Example:
        >>> percentile_rank(500000, 'total_area', stats)
        '< 75th'  # This event's area is between 70th and 75th percentile
    """
    for p in sorted(stats[field]):
        if value < stats[field][p]:
            return f"< {p}th"
    return "≥ 99th"


# ============================================================================
# Main Usage
# ============================================================================

if __name__ == "__main__":
    # Load all events from catalogue
    events = load_events("/data/output/events.jsonl")
    
    # Fields to analyze
    fields = ["total_area", "peak_value", "mean_value", "duration"]
    
    # Compute and display percentile statistics
    stats = compute_percentiles(events, fields)
    print_percentile_summary(stats)
    
    # Example: Classify a single event
    # Uncomment to analyze the first event in the catalogue:
    #
    # event = events[0]
    # print("\nEvent Classification:")
    # for field in fields:
    #     if field == "duration":
    #         value = get_duration(event)
    #     else:
    #         value = event.get(field)
    #     if value is not None:
    #         rank = percentile_rank(value, field, stats)
    #         print(f"{field}: {value:.2f} → {rank}")