#!/usr/bin/env python3
"""Generate visibility windows from TLE data for multiple ground stations."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import subprocess
import sys

def load_ground_stations(stations_file: Path) -> list:
    """Load ground station configurations."""
    with stations_file.open() as f:
        data = json.load(f)
    return data['ground_stations']

def parse_tle_count(tle_file: Path) -> int:
    """Count number of satellites in TLE file."""
    with tle_file.open() as f:
        lines = f.readlines()
    # TLE format: 3 lines per satellite (name, line1, line2)
    return len([l for l in lines if l.strip().startswith('1 ')])

def generate_windows_for_station(tle_file: Path, station: dict,
                                  start: str, end: str,
                                  output_dir: Path) -> Path:
    """Generate visibility windows for one station."""
    output_file = output_dir / f"windows_{station['name'].lower()}_{tle_file.stem}.json"

    cmd = [
        sys.executable,
        'scripts/tle_windows.py',
        '--tle', str(tle_file),
        '--lat', str(station['lat']),
        '--lon', str(station['lon']),
        '--alt', str(station.get('alt', 0) / 1000),  # Convert m to km
        '--start', start,
        '--end', end,
        '--step', '30',
        '--min-elev', '10.0',
        '--out', str(output_file)
    ]

    print(f"Generating windows for {station['name']} from {tle_file.name}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"  ✓ {output_file.name}")
        return output_file
    else:
        print(f"  ✗ Error: {result.stderr}")
        return None

def merge_windows(window_files: list[Path], output_file: Path):
    """Merge multiple window files into one."""
    all_windows = []

    for wf in window_files:
        if wf and wf.exists():
            with wf.open() as f:
                data = json.load(f)
                all_windows.extend(data.get('windows', []))

    merged = {
        'meta': {
            'total_windows': len(all_windows),
            'sources': [str(f) for f in window_files if f],
            'generated_at': datetime.now(timezone.utc).isoformat()
        },
        'windows': all_windows
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open('w') as f:
        json.dump(merged, f, indent=2)

    print(f"\nMerged {len(all_windows)} windows → {output_file}")

def main():
    ap = argparse.ArgumentParser(description="Generate TLE visibility windows for multiple stations")
    ap.add_argument('--tle', type=Path, required=True, help='TLE file')
    ap.add_argument('--stations', type=Path,
                    default=Path('data/taiwan_ground_stations.json'),
                    help='Ground stations JSON')
    ap.add_argument('--start', default='2025-10-08T00:00:00Z', help='Start time (ISO 8601)')
    ap.add_argument('--end', default='2025-10-09T00:00:00Z', help='End time (ISO 8601)')
    ap.add_argument('--output-dir', type=Path, default=Path('data/windows'),
                    help='Output directory for window files')
    ap.add_argument('--merged', type=Path,
                    default=Path('data/merged_tle_windows.json'),
                    help='Merged output file')

    args = ap.parse_args()

    # Load stations
    stations = load_ground_stations(args.stations)
    print(f"Loaded {len(stations)} ground stations")

    # Check TLE file
    sat_count = parse_tle_count(args.tle)
    print(f"TLE file contains {sat_count} satellites")

    # Generate windows for each station
    args.output_dir.mkdir(parents=True, exist_ok=True)
    window_files = []

    for station in stations:
        wf = generate_windows_for_station(
            args.tle, station,
            args.start, args.end,
            args.output_dir
        )
        if wf:
            window_files.append(wf)

    # Merge all windows
    if window_files:
        merge_windows(window_files, args.merged)

    print("\n✅ Window generation complete!")
    return 0

if __name__ == '__main__':
    exit(main())
