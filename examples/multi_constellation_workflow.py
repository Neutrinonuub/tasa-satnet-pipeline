#!/usr/bin/env python3
"""
Multi-Constellation Workflow Example for TASA SatNet Pipeline.

This script demonstrates the complete workflow for processing multiple
satellite constellations (GPS, Iridium, OneWeb, Starlink) with conflict
detection and priority-based scheduling.

Example usage:
    # Step 1: Calculate windows for multiple constellations
    python scripts/multi_constellation.py merge \\
        data/gps.tle data/iridium.tle \\
        -o data/merged_multi.tle

    # Step 2: Calculate contact windows
    python scripts/multi_constellation.py windows \\
        data/merged_multi.tle \\
        --stations data/taiwan_ground_stations.json \\
        -o data/multi_windows.json

    # Step 3: Run this workflow script
    python examples/multi_constellation_workflow.py \\
        --windows data/multi_windows.json \\
        --output-dir results/multi_constellation
"""
from __future__ import annotations
import json
import argparse
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.constellation_manager import ConstellationManager
from scripts.gen_scenario import ScenarioGenerator
from scripts.metrics import MetricsCalculator


def print_section(title: str):
    """Print a section header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def main():
    """Run complete multi-constellation workflow."""
    parser = argparse.ArgumentParser(
        description='Multi-Constellation Workflow Example',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--windows', type=Path, required=True,
                       help='Multi-constellation windows JSON file')
    parser.add_argument('--output-dir', type=Path, default=Path('results/multi_constellation'),
                       help='Output directory for results')
    parser.add_argument('--mode', choices=['transparent', 'regenerative'],
                       default='transparent', help='Relay mode')
    parser.add_argument('--include-rejected', action='store_true',
                       help='Include rejected windows in scenario')

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print_section("MULTI-CONSTELLATION WORKFLOW")
    print(f"Input windows: {args.windows}")
    print(f"Output directory: {args.output_dir}")
    print(f"Relay mode: {args.mode}")

    # ===================================================================
    # STEP 1: Constellation Management
    # ===================================================================
    print_section("STEP 1: Constellation Management")

    manager = ConstellationManager()

    print("Loading windows from JSON...")
    count = manager.load_windows_from_json(args.windows)
    print(f"✓ Loaded {count} windows")

    print("\nDetected constellations:")
    for name, metadata in manager.constellations.items():
        print(f"  - {name}:")
        print(f"      Satellites: {metadata.satellite_count}")
        print(f"      Frequency: {metadata.frequency_band}")
        print(f"      Priority: {metadata.priority}")
        print(f"      Min Elevation: {metadata.min_elevation}°")

    # ===================================================================
    # STEP 2: Conflict Detection
    # ===================================================================
    print_section("STEP 2: Conflict Detection")

    print("Detecting frequency conflicts...")
    conflicts = manager.detect_conflicts()
    print(f"✓ Found {len(conflicts)} conflicts")

    if conflicts:
        print("\nConflict details:")
        for i, conflict in enumerate(conflicts[:5], 1):  # Show first 5
            print(f"  {i}. {conflict['window1']} vs {conflict['window2']}")
            print(f"      Frequency: {conflict['frequency_band']}")
            print(f"      Station: {conflict['ground_station']}")
            print(f"      Overlap: {conflict['overlap_start']} to {conflict['overlap_end']}")

        if len(conflicts) > 5:
            print(f"  ... and {len(conflicts) - 5} more conflicts")

    # Save conflicts
    conflicts_file = args.output_dir / 'conflicts.json'
    with conflicts_file.open('w') as f:
        json.dump({'conflicts': conflicts, 'count': len(conflicts)}, f, indent=2)
    print(f"\n✓ Conflicts saved to {conflicts_file}")

    # ===================================================================
    # STEP 3: Priority Scheduling
    # ===================================================================
    print_section("STEP 3: Priority Scheduling")

    print("Scheduling windows with priority resolution...")
    schedule = manager.get_scheduling_order()
    print(f"✓ Scheduled: {len(schedule['scheduled'])} windows")
    print(f"✓ Rejected: {len(schedule['rejected'])} windows")

    if schedule['rejected']:
        print("\nRejection reasons:")
        rejection_reasons = {}
        for window in schedule['rejected']:
            reason = window.get('reason', 'Unknown')
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

        for reason, count in rejection_reasons.items():
            print(f"  - {reason}: {count}")

    # Save schedule
    schedule_file = args.output_dir / 'schedule.json'
    with schedule_file.open('w') as f:
        json.dump(schedule, f, indent=2)
    print(f"\n✓ Schedule saved to {schedule_file}")

    # ===================================================================
    # STEP 4: Scenario Generation
    # ===================================================================
    print_section("STEP 4: NS-3 Scenario Generation")

    print("Generating NS-3 scenario with constellation metadata...")
    scenario_file = args.output_dir / 'scenario.json'
    scenario = manager.export_to_ns3_scenario(
        scenario_file,
        include_rejected=args.include_rejected,
        mode=args.mode
    )

    print(f"✓ Scenario generated")
    print(f"  Satellites: {scenario['metadata']['total_satellites']}")
    print(f"  Gateways: {scenario['metadata']['total_gateways']}")
    print(f"  Events: {len(scenario['events'])}")
    print(f"  Conflicts: {scenario['metadata']['total_conflicts']}")
    print(f"  Scheduled windows: {scenario['metadata']['scheduled_windows']}")
    print(f"  Rejected windows: {scenario['metadata']['rejected_windows']}")
    print(f"\n✓ Scenario saved to {scenario_file}")

    # ===================================================================
    # STEP 5: Metrics Calculation
    # ===================================================================
    print_section("STEP 5: Metrics Calculation")

    print("Computing metrics with per-constellation tracking...")
    calculator = MetricsCalculator(
        scenario,
        skip_validation=True,
        enable_constellation_metrics=True
    )

    metrics = calculator.compute_all_metrics()
    summary = calculator.generate_summary()

    print(f"✓ Computed {len(metrics)} session metrics")

    # Overall statistics
    print("\nOverall Statistics:")
    print(f"  Total sessions: {summary['total_sessions']}")
    print(f"  Mode: {summary['mode']}")
    print(f"  Mean latency: {summary['latency']['mean_ms']:.2f} ms")
    print(f"  P95 latency: {summary['latency']['p95_ms']:.2f} ms")
    print(f"  Mean throughput: {summary['throughput']['mean_mbps']:.2f} Mbps")
    print(f"  Total duration: {summary['total_duration_sec']:.0f} sec")

    # Per-constellation statistics
    if 'constellation_stats' in summary:
        print("\nPer-Constellation Statistics:")
        for constellation, stats in summary['constellation_stats'].items():
            print(f"\n  {constellation}:")
            print(f"    Sessions: {stats['sessions']}")
            print(f"    Mean latency: {stats['latency']['mean_ms']:.2f} ms")
            print(f"    P95 latency: {stats['latency']['p95_ms']:.2f} ms")
            print(f"    Mean throughput: {stats['throughput']['mean_mbps']:.2f} Mbps")
            print(f"    Total duration: {stats['total_duration_sec']:.0f} sec")

    # Export metrics
    csv_file = args.output_dir / 'metrics.csv'
    calculator.export_csv(csv_file)
    print(f"\n✓ Metrics CSV saved to {csv_file}")

    summary_file = args.output_dir / 'summary.json'
    with summary_file.open('w') as f:
        json.dump(summary, f, indent=2)
    print(f"✓ Summary JSON saved to {summary_file}")

    # ===================================================================
    # STEP 6: Constellation Manager Statistics
    # ===================================================================
    print_section("STEP 6: Constellation Manager Statistics")

    stats = manager.get_constellation_stats()

    print("Constellation Details:")
    for constellation, stat in stats.items():
        print(f"\n  {constellation}:")
        print(f"    Satellites: {stat['metadata']['satellite_count']}")
        print(f"    Frequency band: {stat['metadata']['frequency_band']}")
        print(f"    Priority: {stat['metadata']['priority']}")
        print(f"    Total windows: {stat['total_windows']}")
        print(f"    Scheduled: {stat['scheduled_windows']}")
        print(f"    Rejected: {stat['rejected_windows']}")
        print(f"    Conflicts: {stat['conflicts']}")
        print(f"    Scheduling efficiency: {stat['scheduling_efficiency']:.1f}%")

    print("\nFrequency Band Usage:")
    for band, count in manager.get_frequency_band_usage().items():
        print(f"  {band}: {count} windows")

    print("\nPriority Distribution:")
    for priority, count in manager.get_priority_distribution().items():
        print(f"  {priority}: {count} windows")

    # Save constellation stats
    stats_file = args.output_dir / 'constellation_stats.json'
    with stats_file.open('w') as f:
        json.dump(stats, f, indent=2)
    print(f"\n✓ Constellation stats saved to {stats_file}")

    # ===================================================================
    # SUMMARY
    # ===================================================================
    print_section("WORKFLOW COMPLETE")

    print("Generated files:")
    print(f"  1. Conflicts: {conflicts_file}")
    print(f"  2. Schedule: {schedule_file}")
    print(f"  3. Scenario: {scenario_file}")
    print(f"  4. Metrics CSV: {csv_file}")
    print(f"  5. Summary JSON: {summary_file}")
    print(f"  6. Constellation stats: {stats_file}")

    print("\nNext steps:")
    print("  - Review conflicts and scheduling decisions")
    print("  - Visualize metrics by constellation")
    print("  - Run NS-3 simulation with generated scenario")
    print("  - Analyze per-constellation performance")

    return 0


if __name__ == '__main__':
    exit(main())
