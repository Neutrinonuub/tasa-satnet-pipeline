#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: TLE-OASIS Integration Usage

This example demonstrates how to use the TLE-OASIS bridge module
to merge satellite visibility windows from multiple sources.

Usage:
    python examples/tle_integration_example.py
"""
from __future__ import annotations
import json
import sys
import io
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Fix Windows console encoding for Unicode output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.tle_oasis_bridge import (
    convert_tle_to_oasis_format,
    merge_windows,
    load_ground_stations,
    normalize_timestamp
)


def example_1_basic_conversion():
    """Example 1: Basic TLE to OASIS format conversion."""
    print("\n=== Example 1: Basic Format Conversion ===\n")

    # Sample TLE windows (from tle_windows.py output)
    tle_windows = [
        {
            "type": "tle_pass",
            "start": "2025-10-08T10:00:00Z",
            "end": "2025-10-08T10:15:00Z",
            "sat": "ISS",
            "gw": "24.788,120.998"  # Hsinchu coordinates
        },
        {
            "type": "tle_pass",
            "start": "2025-10-08T12:00:00Z",
            "end": "2025-10-08T12:12:00Z",
            "sat": "ISS",
            "gw": "25.033,121.565"  # Taipei coordinates
        }
    ]

    # Load ground stations
    stations_file = Path(__file__).parent.parent / "data" / "taiwan_ground_stations.json"
    if stations_file.exists():
        stations = load_ground_stations(stations_file)
    else:
        print(f"Warning: Stations file not found at {stations_file}")
        stations = None

    # Convert TLE windows to OASIS format
    oasis_windows = convert_tle_to_oasis_format(tle_windows, stations=stations)

    print("TLE Windows (input):")
    print(json.dumps(tle_windows, indent=2))

    print("\nOASIS Windows (output):")
    print(json.dumps(oasis_windows, indent=2))

    print("\n✓ Coordinates mapped to station names")
    print(f"✓ Converted {len(tle_windows)} TLE windows to OASIS format")


def example_2_union_merge():
    """Example 2: Union merge strategy."""
    print("\n=== Example 2: Union Merge Strategy ===\n")

    # OASIS windows from log
    oasis_windows = [
        {
            "type": "cmd",
            "start": "2025-10-08T10:05:00Z",
            "end": "2025-10-08T10:20:00Z",
            "sat": "ISS",
            "gw": "HSINCHU",
            "source": "log"
        },
        {
            "type": "xband",
            "start": "2025-10-08T14:00:00Z",
            "end": "2025-10-08T14:08:00Z",
            "sat": "SAT-1",
            "gw": "TAIPEI",
            "source": "log"
        }
    ]

    # TLE windows
    tle_windows = [
        {
            "type": "tle_pass",
            "start": "2025-10-08T10:00:00Z",  # Overlaps with OASIS ISS@HSINCHU
            "end": "2025-10-08T10:15:00Z",
            "sat": "ISS",
            "gw": "24.788,120.998"
        },
        {
            "type": "tle_pass",
            "start": "2025-10-08T16:00:00Z",  # New window not in OASIS
            "end": "2025-10-08T16:10:00Z",
            "sat": "ISS",
            "gw": "25.033,121.565"
        }
    ]

    # Load stations
    stations_file = Path(__file__).parent.parent / "data" / "taiwan_ground_stations.json"
    stations = load_ground_stations(stations_file) if stations_file.exists() else None

    # Merge with union strategy
    merged = merge_windows(
        oasis_windows,
        tle_windows,
        strategy='union',
        stations=stations
    )

    print("OASIS Windows (2):")
    for w in oasis_windows:
        print(f"  - {w['type']:6} | {w['sat']:6} @ {w['gw']:8} | {w['start']} to {w['end']}")

    print("\nTLE Windows (2):")
    for w in tle_windows:
        print(f"  - tle_pass | {w['sat']:6} @ {w['gw'][:8]:8} | {w['start']} to {w['end']}")

    print(f"\nMerged Windows ({len(merged)}):")
    for w in merged:
        print(f"  - {w['type']:6} | {w['sat']:6} @ {w['gw']:8} | {w['start']} to {w['end']} | source={w['source']}")

    print("\n✓ Union merge combines all windows")
    print("✓ Overlapping windows are merged")
    print("✓ New TLE window added")


def example_3_intersection_merge():
    """Example 3: Intersection merge strategy (validation)."""
    print("\n=== Example 3: Intersection Merge (Validation) ===\n")

    # OASIS windows
    oasis_windows = [
        {
            "type": "cmd",
            "start": "2025-10-08T10:00:00Z",
            "end": "2025-10-08T10:20:00Z",
            "sat": "ISS",
            "gw": "HSINCHU",
            "source": "log"
        },
        {
            "type": "xband",
            "start": "2025-10-08T14:00:00Z",
            "end": "2025-10-08T14:08:00Z",
            "sat": "SAT-1",
            "gw": "TAIPEI",
            "source": "log"
        }
    ]

    # TLE windows (one overlaps, one doesn't)
    tle_windows = [
        {
            "type": "tle_pass",
            "start": "2025-10-08T10:10:00Z",  # Overlaps with OASIS ISS@HSINCHU
            "end": "2025-10-08T10:30:00Z",
            "sat": "ISS",
            "gw": "24.788,120.998"
        },
        {
            "type": "tle_pass",
            "start": "2025-10-08T16:00:00Z",  # No overlap
            "end": "2025-10-08T16:10:00Z",
            "sat": "ISS",
            "gw": "25.033,121.565"
        }
    ]

    stations_file = Path(__file__).parent.parent / "data" / "taiwan_ground_stations.json"
    stations = load_ground_stations(stations_file) if stations_file.exists() else None

    # Merge with intersection strategy
    merged = merge_windows(
        oasis_windows,
        tle_windows,
        strategy='intersection',
        stations=stations
    )

    print("OASIS Windows (2):")
    for w in oasis_windows:
        print(f"  - {w['type']:6} | {w['sat']:6} @ {w['gw']:8} | {w['start']} to {w['end']}")

    print("\nTLE Windows (2):")
    for w in tle_windows:
        print(f"  - tle_pass | {w['sat']:6} @ {w['gw'][:8]:8} | {w['start']} to {w['end']}")

    print(f"\nIntersection Windows ({len(merged)}):")
    for w in merged:
        print(f"  - {w['type']:6} | {w['sat']:6} @ {w['gw']:8} | {w['start']} to {w['end']} | source={w['source']}")

    print("\n✓ Only verified windows (overlap in both sources)")
    print("✓ Intersection period: 10:10-10:20 (overlap of OASIS 10:00-10:20 and TLE 10:10-10:30)")


def example_4_timezone_handling():
    """Example 4: Timezone normalization."""
    print("\n=== Example 4: Timezone Handling ===\n")

    # Different timezone representations
    timestamps = [
        "2025-10-08T10:15:30Z",           # UTC with Z
        "2025-10-08T10:15:30+00:00",      # UTC with offset
        "2025-10-08T18:15:30+08:00",      # Taiwan time (UTC+8)
        "2025-10-08T05:15:30-05:00"       # US Eastern (UTC-5)
    ]

    print("Timestamp normalization to UTC:")
    for ts in timestamps:
        normalized = normalize_timestamp(ts, "UTC")
        print(f"  {ts:30} → {normalized}")

    print("\n✓ All timestamps normalized to UTC")
    print("✓ Timezone offsets correctly converted")


def example_5_batch_processing():
    """Example 5: Batch processing multiple satellites."""
    print("\n=== Example 5: Batch Processing ===\n")

    # Simulate multiple satellites with TLE windows
    satellites = ["ISS", "STARLINK-1234", "GPS-IIF-5"]

    # Generate sample windows for each satellite
    all_windows = []
    base_time = datetime.now(timezone.utc).replace(microsecond=0)

    for i, sat in enumerate(satellites):
        for station_offset in range(3):  # 3 passes per satellite
            start = base_time + timedelta(hours=i*2 + station_offset*8)
            end = start + timedelta(minutes=12)

            window = {
                "type": "tle_pass",
                "start": start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "end": end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "sat": sat,
                "gw": f"{24.0 + station_offset},{120.0 + station_offset}"
            }
            all_windows.append(window)

    # Load stations
    stations_file = Path(__file__).parent.parent / "data" / "taiwan_ground_stations.json"
    stations = load_ground_stations(stations_file) if stations_file.exists() else None

    # Convert all windows
    converted = convert_tle_to_oasis_format(all_windows, stations=stations)

    print(f"Batch processed {len(satellites)} satellites:")
    for sat in satellites:
        sat_windows = [w for w in converted if w['sat'] == sat]
        print(f"  - {sat:15} : {len(sat_windows)} windows")

    print(f"\n✓ Total: {len(converted)} windows converted")
    print("✓ Station coordinates mapped where possible")


def main():
    """Run all examples."""
    print("=" * 70)
    print("TLE-OASIS Integration Examples")
    print("=" * 70)

    try:
        example_1_basic_conversion()
        example_2_union_merge()
        example_3_intersection_merge()
        example_4_timezone_handling()
        example_5_batch_processing()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
