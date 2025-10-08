#!/usr/bin/env python3
"""
Multi-Constellation Integration Example

Demonstrates complete workflow for processing multiple satellite constellations.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Import multi-constellation tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.multi_constellation import (
    merge_tle_files,
    identify_constellation,
    calculate_mixed_windows,
    detect_conflicts,
    prioritize_scheduling,
    CONSTELLATION_PATTERNS,
    FREQUENCY_BANDS,
    PRIORITY_LEVELS
)


def create_sample_data():
    """Create sample TLE files for demonstration."""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    # Sample GPS TLE (2 satellites)
    gps_tle = data_dir / "example_gps.tle"
    gps_tle.write_text("""GPS BIIA-10 (PRN 32)
1 20959U 90103A   24280.50000000 -.00000027  00000+0  00000+0 0  9998
2 20959  54.9480 187.6771 0115178 208.0806 151.3064  2.00564475123456
GPS BIIR-2  (PRN 13)
1 24876U 97035A   24280.50000000 -.00000027  00000+0  00000+0 0  9999
2 24876  55.4289 127.3456 0078456 189.2345 170.5678  2.00561234234567
""")

    # Sample Iridium TLE (2 satellites)
    iridium_tle = data_dir / "example_iridium.tle"
    iridium_tle.write_text("""IRIDIUM 102
1 24794U 97020B   24280.50000000  .00000067  00000+0  16962-4 0  9992
2 24794  86.3945  54.2881 0002341  89.5678 270.5755 14.34218475456789
IRIDIUM 106
1 24840U 97030C   24280.50000000  .00000067  00000+0  16962-4 0  9993
2 24840  86.3945 123.4567 0002341 123.4567 236.5432 14.34218475567890
""")

    # Sample Starlink TLE (2 satellites)
    starlink_tle = data_dir / "example_starlink.tle"
    starlink_tle.write_text("""STARLINK-1007
1 44713U 19074A   24280.50000000  .00001234  00000+0  12345-3 0  9990
2 44713  53.0012 123.4567 0001234  78.9012 281.2345 15.12345678123456
STARLINK-1008
1 44714U 19074B   24280.50000000  .00001234  00000+0  12345-3 0  9991
2 44714  53.0012 123.4567 0001234  78.9012 281.2345 15.12345678123457
""")

    return gps_tle, iridium_tle, starlink_tle


def example_1_constellation_identification():
    """Example 1: Constellation identification."""
    print("=" * 70)
    print("Example 1: Constellation Identification")
    print("=" * 70)

    satellites = [
        "GPS BIIA-10 (PRN 32)",
        "IRIDIUM 102",
        "ONEWEB-0001",
        "STARLINK-1007",
        "ISS (ZARYA)",
    ]

    for sat_name in satellites:
        constellation = identify_constellation(sat_name)
        freq_band = FREQUENCY_BANDS.get(constellation, "Unknown")
        priority = PRIORITY_LEVELS.get(constellation, "Unknown")

        print(f"\n{sat_name}:")
        print(f"  Constellation: {constellation}")
        print(f"  Frequency:     {freq_band}")
        print(f"  Priority:      {priority}")

    print()


def example_2_tle_merging():
    """Example 2: Merge multiple TLE files."""
    print("=" * 70)
    print("Example 2: TLE File Merging")
    print("=" * 70)

    # Create sample data
    gps_tle, iridium_tle, starlink_tle = create_sample_data()

    # Merge TLEs
    output_dir = Path(__file__).parent.parent / "data"
    merged_tle = output_dir / "example_merged.tle"

    print(f"\nMerging TLE files:")
    print(f"  - {gps_tle.name}")
    print(f"  - {iridium_tle.name}")
    print(f"  - {starlink_tle.name}")

    stats = merge_tle_files([gps_tle, iridium_tle, starlink_tle], merged_tle)

    print(f"\nMerge Statistics:")
    print(f"  Total satellites:    {stats['total_satellites']}")
    print(f"  Constellations:      {', '.join(stats['constellations'])}")
    print(f"  Duplicates removed:  {stats['duplicates_removed']}")
    print(f"  Output file:         {merged_tle}")
    print()

    return merged_tle


def example_3_window_calculation(merged_tle):
    """Example 3: Calculate contact windows."""
    print("=" * 70)
    print("Example 3: Contact Window Calculation")
    print("=" * 70)

    # Define ground stations (Taiwan)
    stations = [
        {
            "name": "TASA-Taipei",
            "lat": 25.0330,
            "lon": 121.5654,
            "alt": 0
        },
        {
            "name": "TASA-Taichung",
            "lat": 24.7874,
            "lon": 120.9971,
            "alt": 0
        }
    ]

    print(f"\nGround Stations:")
    for station in stations:
        print(f"  - {station['name']}: ({station['lat']:.4f}, {station['lon']:.4f})")

    # Calculate windows around TLE epoch
    start_time = datetime(2024, 10, 6, 0, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(hours=24)

    print(f"\nTime Range:")
    print(f"  Start: {start_time.isoformat()}")
    print(f"  End:   {end_time.isoformat()}")

    result = calculate_mixed_windows(
        merged_tle,
        stations,
        start_time,
        end_time,
        min_elevation=5.0,  # Lower for more passes
        step_seconds=30
    )

    print(f"\nCalculation Results:")
    print(f"  Constellations:  {', '.join(result['meta']['constellations'])}")
    print(f"  Total windows:   {result['meta']['count']}")

    # Show first few windows
    if result['windows']:
        print(f"\nFirst 5 Windows:")
        for i, window in enumerate(result['windows'][:5], 1):
            print(f"\n  Window {i}:")
            print(f"    Satellite:      {window['satellite']}")
            print(f"    Constellation:  {window['constellation']}")
            print(f"    Frequency:      {window['frequency_band']}")
            print(f"    Priority:       {window['priority']}")
            print(f"    Station:        {window['ground_station']}")
            print(f"    Start:          {window['start']}")
            print(f"    Duration:       {window['duration_sec']} sec")
            print(f"    Max Elevation:  {window['max_elevation']:.1f}°")
    else:
        print("\n  No windows calculated (satellites may not pass over stations)")

    print()
    return result


def example_4_conflict_detection(windows_result):
    """Example 4: Detect frequency conflicts."""
    print("=" * 70)
    print("Example 4: Conflict Detection")
    print("=" * 70)

    conflicts = detect_conflicts(windows_result['windows'], FREQUENCY_BANDS)

    print(f"\nConflict Detection Results:")
    print(f"  Total conflicts: {len(conflicts)}")

    if conflicts:
        print(f"\nConflict Details:")
        for i, conflict in enumerate(conflicts[:5], 1):  # Show first 5
            print(f"\n  Conflict {i}:")
            print(f"    Type:          {conflict['type']}")
            print(f"    Window 1:      {conflict['window1']} ({conflict['constellation1']})")
            print(f"    Window 2:      {conflict['window2']} ({conflict['constellation2']})")
            print(f"    Frequency:     {conflict['frequency_band']}")
            print(f"    Station:       {conflict['ground_station']}")
            print(f"    Overlap:       {conflict['overlap_start']} to {conflict['overlap_end']}")
    else:
        print("  No conflicts detected!")

    print()
    return conflicts


def example_5_priority_scheduling(windows_result):
    """Example 5: Priority-based scheduling."""
    print("=" * 70)
    print("Example 5: Priority-Based Scheduling")
    print("=" * 70)

    schedule = prioritize_scheduling(windows_result['windows'], PRIORITY_LEVELS)

    print(f"\nScheduling Results:")
    print(f"  Scheduled windows: {len(schedule['scheduled'])}")
    print(f"  Rejected windows:  {len(schedule['rejected'])}")

    # Statistics by priority
    priority_stats = {'high': 0, 'medium': 0, 'low': 0}
    for window in schedule['scheduled']:
        priority_stats[window['priority']] += 1

    print(f"\nScheduled by Priority:")
    print(f"  High priority:    {priority_stats['high']}")
    print(f"  Medium priority:  {priority_stats['medium']}")
    print(f"  Low priority:     {priority_stats['low']}")

    # Show rejected windows
    if schedule['rejected']:
        print(f"\nRejected Windows (first 5):")
        for i, window in enumerate(schedule['rejected'][:5], 1):
            print(f"\n  Rejected {i}:")
            print(f"    Satellite:      {window['satellite']}")
            print(f"    Constellation:  {window['constellation']}")
            print(f"    Priority:       {window['priority']}")
            print(f"    Reason:         {window['reason']}")
            if window.get('conflict_with'):
                print(f"    Conflict with:  {window['conflict_with']}")

    print()
    return schedule


def example_6_full_pipeline():
    """Example 6: Complete processing pipeline."""
    print("=" * 70)
    print("Example 6: Complete Processing Pipeline")
    print("=" * 70)

    # Create sample data
    gps_tle, iridium_tle, starlink_tle = create_sample_data()

    # Define parameters
    stations = [
        {"name": "TASA-1", "lat": 25.033, "lon": 121.565, "alt": 0}
    ]
    start_time = datetime(2024, 10, 6, 0, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(hours=24)

    print("\nPipeline Steps:")

    # Step 1: Merge
    print("\n  [1/4] Merging TLE files...")
    output_dir = Path(__file__).parent.parent / "data"
    merged_tle = output_dir / "pipeline_merged.tle"
    merge_stats = merge_tle_files([gps_tle, iridium_tle, starlink_tle], merged_tle)
    print(f"        → {merge_stats['total_satellites']} satellites merged")

    # Step 2: Calculate windows
    print("\n  [2/4] Calculating contact windows...")
    windows_result = calculate_mixed_windows(
        merged_tle, stations, start_time, end_time, min_elevation=5.0
    )
    print(f"        → {windows_result['meta']['count']} windows calculated")

    # Step 3: Detect conflicts
    print("\n  [3/4] Detecting conflicts...")
    conflicts = detect_conflicts(windows_result['windows'], FREQUENCY_BANDS)
    print(f"        → {len(conflicts)} conflicts found")

    # Step 4: Schedule
    print("\n  [4/4] Scheduling with priorities...")
    schedule = prioritize_scheduling(windows_result['windows'], PRIORITY_LEVELS)
    print(f"        → {len(schedule['scheduled'])} scheduled, {len(schedule['rejected'])} rejected")

    # Final output
    output_file = output_dir / "pipeline_result.json"
    final_result = {
        'meta': {
            **windows_result['meta'],
            'conflicts': len(conflicts),
            'scheduled': len(schedule['scheduled']),
            'rejected': len(schedule['rejected'])
        },
        'windows': windows_result['windows'],
        'conflicts': conflicts,
        'schedule': schedule
    }

    output_file.write_text(json.dumps(final_result, indent=2))
    print(f"\n  Results saved to: {output_file}")

    print("\nPipeline Summary:")
    print(f"  Constellations:  {', '.join(final_result['meta']['constellations'])}")
    print(f"  Total windows:   {final_result['meta']['count']}")
    print(f"  Conflicts:       {final_result['meta']['conflicts']}")
    print(f"  Scheduled:       {final_result['meta']['scheduled']}")
    print(f"  Rejected:        {final_result['meta']['rejected']}")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║     Multi-Constellation Integration Tool - Examples               ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()

    # Run examples
    example_1_constellation_identification()

    merged_tle = example_2_tle_merging()

    windows_result = example_3_window_calculation(merged_tle)

    if windows_result['windows']:
        example_4_conflict_detection(windows_result)
        example_5_priority_scheduling(windows_result)
    else:
        print("Skipping conflict detection and scheduling (no windows calculated)")
        print()

    example_6_full_pipeline()

    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
