#!/usr/bin/env python3
"""
Starlink Batch Processor Demo

Demonstrates the usage of the Starlink 100 satellite batch processor.
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from starlink_batch_processor import (
    extract_starlink_subset,
    calculate_batch_windows,
    merge_station_windows,
    compute_coverage_stats,
    StarlinkBatchProcessor
)
import json


def demo_01_extract_satellites():
    """Demo 1: Extract satellite subset from TLE file."""
    print("\n" + "="*70)
    print("DEMO 1: Extract Satellite Subset")
    print("="*70)

    tle_file = Path("data/starlink.tle")

    # Extract 20 satellites
    satellites = extract_starlink_subset(tle_file, count=20)

    print(f"Extracted {len(satellites)} satellites from {tle_file.name}")
    print(f"\nFirst 5 satellites:")
    for i, sat in enumerate(satellites[:5], 1):
        print(f"  {i}. {sat['name']}")

    return satellites


def demo_02_calculate_windows(satellites):
    """Demo 2: Calculate visibility windows for multiple stations."""
    print("\n" + "="*70)
    print("DEMO 2: Calculate Visibility Windows")
    print("="*70)

    # Define Taiwan ground stations
    stations = [
        {"name": "HSINCHU", "lat": 24.8, "lon": 120.99, "alt": 0.1},
        {"name": "TAIPEI", "lat": 25.03, "lon": 121.56, "alt": 0.05},
        {"name": "KAOHSIUNG", "lat": 22.63, "lon": 120.30, "alt": 0.01}
    ]

    time_range = {
        'start': '2025-10-08T00:00:00Z',
        'end': '2025-10-08T03:00:00Z'
    }

    print(f"Calculating windows for {len(satellites)} satellites")
    print(f"Time range: {time_range['start']} to {time_range['end']}")
    print(f"Stations: {[s['name'] for s in stations]}")

    windows = calculate_batch_windows(
        satellites=satellites[:10],  # Use first 10 for demo
        stations=stations,
        time_range=time_range,
        min_elevation=10.0,
        parallel=True,
        show_progress=True
    )

    print(f"\nFound {len(windows)} visibility windows")

    # Show sample windows
    print("\nSample windows:")
    for window in windows[:5]:
        print(f"  {window['satellite']:20s} -> {window['station']:10s} "
              f"{window['start']} to {window['end']} "
              f"({window['duration_sec']:.0f}s)")

    return windows, stations


def demo_03_merge_and_stats(windows, stations):
    """Demo 3: Merge windows and compute statistics."""
    print("\n" + "="*70)
    print("DEMO 3: Merge Windows and Compute Statistics")
    print("="*70)

    # Merge windows
    merged = merge_station_windows([windows])

    print(f"Total windows: {merged['meta']['total_windows']}")
    print(f"Stations covered: {merged['meta']['station_count']}")
    print(f"Satellites tracked: {merged['meta']['total_satellites']}")

    # Compute coverage statistics
    stats = compute_coverage_stats(merged, stations)

    print("\nPer-Station Coverage:")
    for station_name, station_stats in stats['coverage_by_station'].items():
        print(f"  {station_name:12s}: {station_stats['window_count']:3d} windows, "
              f"{station_stats['total_duration_sec']:6.0f}s total, "
              f"{station_stats['time_coverage_pct']:5.1f}% coverage")

    print("\nSatellite Distribution:")
    for sat, count in sorted(stats['satellite_distribution'].items(),
                             key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {sat:20s}: {count} windows")

    return merged, stats


def demo_04_full_pipeline():
    """Demo 4: Run full pipeline with StarlinkBatchProcessor."""
    print("\n" + "="*70)
    print("DEMO 4: Full Pipeline Processing")
    print("="*70)

    # Initialize processor
    processor = StarlinkBatchProcessor(
        tle_file=Path("data/starlink.tle"),
        stations_file=Path("data/taiwan_ground_stations.json"),
        satellite_count=50,
        output_file=Path("data/demo_output.json")
    )

    print(f"Processor initialized:")
    print(f"  TLE file: {processor.tle_file}")
    print(f"  Stations: {len(processor.stations)}")
    print(f"  Satellite count: {processor.satellite_count}")

    # Run processing
    print("\nRunning full pipeline...")
    result = processor.run(
        start_time='2025-10-08T00:00:00Z',
        end_time='2025-10-08T06:00:00Z',
        min_elevation=10.0,
        step_sec=30,
        show_progress=True,
        track_memory=True
    )

    if result['status'] == 'success':
        print("\nProcessing Results:")
        print(f"  Status: {result['status']}")
        print(f"  Duration: {result['performance']['duration_sec']:.2f}s")
        print(f"  Windows: {result['performance']['windows_generated']}")
        print(f"  Output: {result['output_file']}")

        if 'peak_memory_mb' in result['statistics']:
            print(f"  Memory: {result['statistics']['peak_memory_mb']:.1f} MB")

        print("\nTop 3 Stations by Coverage:")
        coverage = result['statistics']['coverage_by_station']
        top_stations = sorted(coverage.items(),
                            key=lambda x: x[1]['time_coverage_pct'],
                            reverse=True)[:3]

        for i, (station, stats) in enumerate(top_stations, 1):
            print(f"  {i}. {station}: {stats['time_coverage_pct']:.1f}% "
                  f"({stats['window_count']} windows)")

    return result


def demo_05_export_and_analysis():
    """Demo 5: Export results and basic analysis."""
    print("\n" + "="*70)
    print("DEMO 5: Export and Analysis")
    print("="*70)

    # Load previous results
    output_file = Path("data/demo_output.json")

    if output_file.exists():
        with output_file.open('r', encoding='utf-8') as f:
            data = json.load(f)

        windows = data['windows']

        # Analysis 1: Average pass duration per station
        print("\nAverage Pass Duration by Station:")
        station_durations = {}
        for window in windows:
            station = window['station']
            if station not in station_durations:
                station_durations[station] = []
            station_durations[station].append(window['duration_sec'])

        for station, durations in sorted(station_durations.items()):
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            print(f"  {station:12s}: avg={avg_duration:5.0f}s, max={max_duration:5.0f}s, "
                  f"passes={len(durations)}")

        # Analysis 2: Peak elevation statistics
        print("\nElevation Statistics:")
        elevations = [w['elevation_max'] for w in windows if 'elevation_max' in w]
        if elevations:
            print(f"  Max elevation: {max(elevations):.1f}°")
            print(f"  Avg elevation: {sum(elevations)/len(elevations):.1f}°")
            print(f"  Min elevation: {min(elevations):.1f}°")

        # Analysis 3: Coverage gaps
        print("\nCoverage Timeline Analysis:")
        from datetime import datetime

        # Sort windows by start time
        sorted_windows = sorted(windows, key=lambda w: w['start'])

        # Find longest gap
        max_gap = 0
        max_gap_time = None

        for i in range(len(sorted_windows) - 1):
            end1 = datetime.fromisoformat(sorted_windows[i]['end'].replace('Z', '+00:00'))
            start2 = datetime.fromisoformat(sorted_windows[i+1]['start'].replace('Z', '+00:00'))
            gap = (start2 - end1).total_seconds()

            if gap > max_gap:
                max_gap = gap
                max_gap_time = (end1, start2)

        if max_gap_time:
            print(f"  Longest gap: {max_gap/60:.1f} minutes")
            print(f"    From: {max_gap_time[0].isoformat()}")
            print(f"    To:   {max_gap_time[1].isoformat()}")
    else:
        print(f"Output file not found: {output_file}")


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("Starlink Batch Processor - Comprehensive Demo")
    print("="*70)

    try:
        # Demo 1: Extract satellites
        satellites = demo_01_extract_satellites()

        # Demo 2: Calculate windows
        windows, stations = demo_02_calculate_windows(satellites)

        # Demo 3: Merge and statistics
        merged, stats = demo_03_merge_and_stats(windows, stations)

        # Demo 4: Full pipeline
        result = demo_04_full_pipeline()

        # Demo 5: Export and analysis
        demo_05_export_and_analysis()

        print("\n" + "="*70)
        print("All demos completed successfully!")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
