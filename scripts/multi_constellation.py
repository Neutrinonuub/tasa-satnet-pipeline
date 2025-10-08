#!/usr/bin/env python3
"""
Multi-Constellation Integration Tool for TASA SatNet Pipeline.

Handles merging, identification, and scheduling of multiple satellite
constellations (GPS, Iridium, OneWeb, Starlink, etc.) with conflict
detection and priority-based scheduling.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict

# Try to import TLE processor
try:
    from scripts.tle_processor import (
        TLEProcessor, GroundStation, PassWindow, load_tle_file
    )
    TLE_PROCESSOR_AVAILABLE = True
except ImportError:
    TLE_PROCESSOR_AVAILABLE = False
    print("Warning: tle_processor not available. Limited functionality.")


# Constellation identification patterns
CONSTELLATION_PATTERNS = {
    'GPS': [
        r'GPS',
        r'NAVSTAR',
        r'PRN\s+\d+',
    ],
    'Iridium': [
        r'IRIDIUM',
    ],
    'OneWeb': [
        r'ONEWEB',
    ],
    'Starlink': [
        r'STARLINK',
    ],
    'Globalstar': [
        r'GLOBALSTAR',
    ],
    'O3B': [
        r'O3B',
    ],
}


# Frequency band mapping for each constellation
FREQUENCY_BANDS = {
    'GPS': 'L-band',          # L1: 1575.42 MHz, L2: 1227.60 MHz
    'Iridium': 'Ka-band',     # 23.18-23.38 GHz downlink
    'OneWeb': 'Ku-band',      # 10.7-12.7 GHz downlink
    'Starlink': 'Ka-band',    # 17.8-20.2 GHz downlink
    'Globalstar': 'L-band',   # 1610-1626.5 MHz
    'O3B': 'Ka-band',         # 17.7-20.2 GHz
    'Unknown': 'Unknown',
}


# Priority levels for each constellation
PRIORITY_LEVELS = {
    'GPS': 'high',           # Navigation critical
    'Iridium': 'medium',     # Commercial voice/data
    'OneWeb': 'low',         # Commercial broadband
    'Starlink': 'low',       # Commercial broadband
    'Globalstar': 'medium',  # Commercial satellite phone
    'O3B': 'medium',         # Commercial backhaul
    'Unknown': 'low',
}


# Priority ordering for scheduling
PRIORITY_ORDER = {'high': 0, 'medium': 1, 'low': 2}


@dataclass
class ConstellationConfig:
    """Configuration for a satellite constellation."""
    name: str
    pattern: str
    frequency_band: str
    priority: str
    min_elevation: float = 10.0  # degrees


def identify_constellation(satellite_name: str) -> str:
    """
    Identify which constellation a satellite belongs to.

    Args:
        satellite_name: Name of the satellite

    Returns:
        Constellation name (GPS, Iridium, OneWeb, Starlink, etc.) or 'Unknown'
    """
    sat_upper = satellite_name.upper()

    for constellation, patterns in CONSTELLATION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, sat_upper):
                return constellation

    return 'Unknown'


def merge_tle_files(tle_files: List[Path], output_file: Path) -> Dict:
    """
    Merge multiple TLE files into a single file.

    Args:
        tle_files: List of TLE file paths
        output_file: Output merged TLE file path

    Returns:
        Statistics dictionary with merge info
    """
    seen_norad_ids = set()
    merged_lines = []
    constellations_found = set()
    duplicates = 0

    for tle_file in tle_files:
        if not tle_file.exists():
            print(f"Warning: TLE file not found: {tle_file}")
            continue

        with tle_file.open('r') as f:
            lines = [l.strip() for l in f if l.strip()]

        # Process TLE entries (name, line1, line2)
        for i in range(0, len(lines), 3):
            if i + 2 >= len(lines):
                break

            name = lines[i]
            line1 = lines[i + 1]
            line2 = lines[i + 2]

            # Verify TLE format
            if not (line1.startswith('1 ') and line2.startswith('2 ')):
                continue

            # Extract NORAD catalog number for deduplication
            try:
                norad_id = line1.split()[1].rstrip('U')
                if norad_id in seen_norad_ids:
                    duplicates += 1
                    continue

                seen_norad_ids.add(norad_id)
            except (IndexError, ValueError):
                continue

            # Identify constellation
            constellation = identify_constellation(name)
            constellations_found.add(constellation)

            # Add to merged output
            merged_lines.extend([name, line1, line2])

    # Write merged file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open('w') as f:
        for line in merged_lines:
            f.write(line + '\n')

    stats = {
        'total_satellites': len(seen_norad_ids),
        'constellations': sorted(list(constellations_found - {'Unknown'})),
        'duplicates_removed': duplicates,
        'output_file': str(output_file)
    }

    return stats


def calculate_mixed_windows(
    tle_file: Path,
    stations: List[Dict],
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    min_elevation: float = 10.0,
    step_seconds: int = 60
) -> Dict:
    """
    Calculate contact windows for mixed constellation.

    Args:
        tle_file: Path to merged TLE file
        stations: List of ground station dicts with name, lat, lon, alt
        start_time: Start of calculation window (default: now)
        end_time: End of calculation window (default: +24h)
        min_elevation: Minimum elevation angle in degrees
        step_seconds: Time step for propagation

    Returns:
        Dictionary with meta and windows
    """
    if not TLE_PROCESSOR_AVAILABLE:
        return {
            'meta': {
                'error': 'TLE processor not available',
                'constellations': [],
                'total_satellites': 0
            },
            'windows': []
        }

    # Default time range
    if start_time is None:
        start_time = datetime.now(timezone.utc)
    if end_time is None:
        end_time = start_time + timedelta(days=1)

    # Load TLE file
    processors = load_tle_file(tle_file)

    # Identify constellations
    constellations_found = set()
    for proc in processors:
        constellation = identify_constellation(proc.satellite_name)
        constellations_found.add(constellation)

    # Compute passes for all satellites and stations
    all_windows = []
    for proc in processors:
        constellation = identify_constellation(proc.satellite_name)
        freq_band = FREQUENCY_BANDS.get(constellation, 'Unknown')
        priority = PRIORITY_LEVELS.get(constellation, 'low')

        for station in stations:
            observer = GroundStation(
                name=station['name'],
                lat=station['lat'],
                lon=station['lon'],
                alt=station.get('alt', 0.0)
            )

            passes = proc.compute_passes(
                observer, start_time, end_time, min_elevation, step_seconds
            )

            for pass_window in passes:
                all_windows.append({
                    'satellite': pass_window.satellite,
                    'constellation': constellation,
                    'frequency_band': freq_band,
                    'priority': priority,
                    'ground_station': pass_window.ground_station,
                    'start': pass_window.start.isoformat().replace('+00:00', 'Z'),
                    'end': pass_window.end.isoformat().replace('+00:00', 'Z'),
                    'max_elevation': round(pass_window.max_elevation, 2),
                    'duration_sec': int((pass_window.end - pass_window.start).total_seconds())
                })

    # Sort by start time
    all_windows.sort(key=lambda w: w['start'])

    result = {
        'meta': {
            'constellations': sorted(list(constellations_found - {'Unknown'})),
            'total_satellites': len(processors),
            'ground_stations': [s['name'] for s in stations],
            'start': start_time.isoformat().replace('+00:00', 'Z'),
            'end': end_time.isoformat().replace('+00:00', 'Z'),
            'count': len(all_windows)
        },
        'windows': all_windows
    }

    return result


def detect_conflicts(windows: List[Dict], frequency_bands: Dict) -> List[Dict]:
    """
    Detect frequency conflicts between windows.

    Conflicts occur when:
    - Same ground station
    - Same frequency band
    - Overlapping time windows

    Args:
        windows: List of window dictionaries
        frequency_bands: Frequency band mapping

    Returns:
        List of conflict dictionaries
    """
    conflicts = []

    # Group windows by ground station
    by_station = defaultdict(list)
    for window in windows:
        by_station[window['ground_station']].append(window)

    # Check each station for conflicts
    for station, station_windows in by_station.items():
        # Group by frequency band
        by_band = defaultdict(list)
        for window in station_windows:
            by_band[window['frequency_band']].append(window)

        # Check each frequency band for time overlaps
        for band, band_windows in by_band.items():
            if band == 'Unknown':
                continue

            # Check all pairs for overlap
            for i in range(len(band_windows)):
                for j in range(i + 1, len(band_windows)):
                    w1 = band_windows[i]
                    w2 = band_windows[j]

                    # Parse times
                    start1 = datetime.fromisoformat(w1['start'].replace('Z', '+00:00'))
                    end1 = datetime.fromisoformat(w1['end'].replace('Z', '+00:00'))
                    start2 = datetime.fromisoformat(w2['start'].replace('Z', '+00:00'))
                    end2 = datetime.fromisoformat(w2['end'].replace('Z', '+00:00'))

                    # Check for overlap
                    if not (end1 <= start2 or end2 <= start1):
                        conflicts.append({
                            'type': 'frequency_conflict',
                            'window1': w1['satellite'],
                            'window2': w2['satellite'],
                            'constellation1': w1['constellation'],
                            'constellation2': w2['constellation'],
                            'frequency_band': band,
                            'ground_station': station,
                            'overlap_start': max(start1, start2).isoformat().replace('+00:00', 'Z'),
                            'overlap_end': min(end1, end2).isoformat().replace('+00:00', 'Z')
                        })

    return conflicts


def prioritize_scheduling(windows: List[Dict], priorities: Dict) -> Dict:
    """
    Priority-based scheduling with conflict resolution.

    Args:
        windows: List of window dictionaries
        priorities: Priority level mapping

    Returns:
        Dictionary with 'scheduled' and 'rejected' windows
    """
    # Sort windows by priority then by start time
    def priority_key(window):
        priority = window.get('priority', 'low')
        start = datetime.fromisoformat(window['start'].replace('Z', '+00:00'))
        return (PRIORITY_ORDER.get(priority, 999), start)

    sorted_windows = sorted(windows, key=priority_key)

    # Track scheduled windows per station and frequency band
    scheduled = []
    rejected = []
    station_band_schedule = defaultdict(list)  # (station, band) -> [windows]

    for window in sorted_windows:
        station = window['ground_station']
        band = window['frequency_band']
        key = (station, band)

        # Skip unknown bands
        if band == 'Unknown':
            rejected.append({
                **window,
                'reason': 'Unknown frequency band',
                'conflict_with': None
            })
            continue

        # Check for conflicts with already scheduled windows
        start = datetime.fromisoformat(window['start'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(window['end'].replace('Z', '+00:00'))

        has_conflict = False
        conflict_with = None

        for scheduled_window in station_band_schedule[key]:
            s_start = datetime.fromisoformat(scheduled_window['start'].replace('Z', '+00:00'))
            s_end = datetime.fromisoformat(scheduled_window['end'].replace('Z', '+00:00'))

            # Check for overlap
            if not (end <= s_start or s_end <= start):
                has_conflict = True
                conflict_with = scheduled_window['satellite']
                break

        if has_conflict:
            rejected.append({
                **window,
                'reason': 'Frequency conflict with higher priority window',
                'conflict_with': conflict_with
            })
        else:
            scheduled.append(window)
            station_band_schedule[key].append(window)

    return {
        'scheduled': scheduled,
        'rejected': rejected
    }


def main():
    """CLI interface for multi-constellation processing."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Multi-Constellation Integration Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge TLE files
  python scripts/multi_constellation.py merge data/gps.tle data/iridium.tle -o data/merged.tle

  # Calculate windows
  python scripts/multi_constellation.py windows data/merged.tle \\
    --stations '{"name":"TASA-1","lat":25.033,"lon":121.565,"alt":0}' \\
    -o data/windows.json

  # Detect conflicts
  python scripts/multi_constellation.py conflicts data/windows.json -o data/conflicts.json

  # Schedule with priorities
  python scripts/multi_constellation.py schedule data/windows.json -o data/schedule.json

  # Full pipeline
  python scripts/multi_constellation.py pipeline data/gps.tle data/iridium.tle \\
    --stations '{"name":"TASA-1","lat":25.033,"lon":121.565,"alt":0}' \\
    -o data/results.json
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Merge command
    merge_parser = subparsers.add_parser('merge', help='Merge multiple TLE files')
    merge_parser.add_argument('tle_files', nargs='+', type=Path, help='TLE files to merge')
    merge_parser.add_argument('-o', '--output', type=Path, required=True,
                             help='Output merged TLE file')

    # Windows command
    windows_parser = subparsers.add_parser('windows', help='Calculate contact windows')
    windows_parser.add_argument('tle_file', type=Path, help='TLE file (can be merged)')
    windows_parser.add_argument('--stations', type=json.loads, nargs='+', required=True,
                               help='Ground stations as JSON dicts')
    windows_parser.add_argument('--start', help='Start time (ISO 8601)')
    windows_parser.add_argument('--end', help='End time (ISO 8601)')
    windows_parser.add_argument('--min-elevation', type=float, default=10.0,
                               help='Minimum elevation (degrees)')
    windows_parser.add_argument('-o', '--output', type=Path, required=True,
                               help='Output windows JSON file')

    # Conflicts command
    conflicts_parser = subparsers.add_parser('conflicts', help='Detect conflicts')
    conflicts_parser.add_argument('windows_file', type=Path, help='Windows JSON file')
    conflicts_parser.add_argument('-o', '--output', type=Path, required=True,
                                 help='Output conflicts JSON file')

    # Schedule command
    schedule_parser = subparsers.add_parser('schedule', help='Priority scheduling')
    schedule_parser.add_argument('windows_file', type=Path, help='Windows JSON file')
    schedule_parser.add_argument('-o', '--output', type=Path, required=True,
                                help='Output schedule JSON file')

    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Full processing pipeline')
    pipeline_parser.add_argument('tle_files', nargs='+', type=Path, help='TLE files')
    pipeline_parser.add_argument('--stations', type=json.loads, nargs='+', required=True,
                                help='Ground stations as JSON dicts')
    pipeline_parser.add_argument('--start', help='Start time (ISO 8601)')
    pipeline_parser.add_argument('--end', help='End time (ISO 8601)')
    pipeline_parser.add_argument('--min-elevation', type=float, default=10.0,
                                help='Minimum elevation (degrees)')
    pipeline_parser.add_argument('-o', '--output', type=Path, required=True,
                                help='Output results JSON file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == 'merge':
        stats = merge_tle_files(args.tle_files, args.output)
        print(f"Merged {stats['total_satellites']} satellites")
        print(f"Constellations: {', '.join(stats['constellations'])}")
        print(f"Duplicates removed: {stats['duplicates_removed']}")
        print(f"Output: {stats['output_file']}")

    elif args.command == 'windows':
        start_time = datetime.fromisoformat(args.start) if args.start else None
        end_time = datetime.fromisoformat(args.end) if args.end else None

        result = calculate_mixed_windows(
            args.tle_file, args.stations, start_time, end_time, args.min_elevation
        )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2))
        print(f"Calculated {result['meta']['count']} windows")
        print(f"Constellations: {', '.join(result['meta']['constellations'])}")
        print(f"Output: {args.output}")

    elif args.command == 'conflicts':
        data = json.loads(args.windows_file.read_text())
        conflicts = detect_conflicts(data['windows'], FREQUENCY_BANDS)

        output = {'conflicts': conflicts, 'count': len(conflicts)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2))
        print(f"Detected {len(conflicts)} conflicts")
        print(f"Output: {args.output}")

    elif args.command == 'schedule':
        data = json.loads(args.windows_file.read_text())
        result = prioritize_scheduling(data['windows'], PRIORITY_LEVELS)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2))
        print(f"Scheduled: {len(result['scheduled'])} windows")
        print(f"Rejected: {len(result['rejected'])} windows")
        print(f"Output: {args.output}")

    elif args.command == 'pipeline':
        # Step 1: Merge TLEs
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tle', delete=False) as tmp:
            merged_tle = Path(tmp.name)

        merge_stats = merge_tle_files(args.tle_files, merged_tle)
        print(f"Step 1: Merged {merge_stats['total_satellites']} satellites")

        # Step 2: Calculate windows
        start_time = datetime.fromisoformat(args.start) if args.start else None
        end_time = datetime.fromisoformat(args.end) if args.end else None

        windows_result = calculate_mixed_windows(
            merged_tle, args.stations, start_time, end_time, args.min_elevation
        )
        print(f"Step 2: Calculated {windows_result['meta']['count']} windows")

        # Step 3: Detect conflicts
        conflicts = detect_conflicts(windows_result['windows'], FREQUENCY_BANDS)
        print(f"Step 3: Detected {len(conflicts)} conflicts")

        # Step 4: Schedule
        schedule_result = prioritize_scheduling(windows_result['windows'], PRIORITY_LEVELS)
        print(f"Step 4: Scheduled {len(schedule_result['scheduled'])} windows")

        # Build final output
        output = {
            'meta': {
                **windows_result['meta'],
                'conflicts': len(conflicts),
                'scheduled': len(schedule_result['scheduled']),
                'rejected': len(schedule_result['rejected'])
            },
            'windows': windows_result['windows'],
            'conflicts': conflicts,
            'schedule': schedule_result
        }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2))
        print(f"\nPipeline complete!")
        print(f"Output: {args.output}")

        # Cleanup temp file
        merged_tle.unlink()

    return 0


if __name__ == "__main__":
    exit(main())
