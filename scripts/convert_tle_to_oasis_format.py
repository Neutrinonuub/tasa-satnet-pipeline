#!/usr/bin/env python3
"""Convert TLE windows format to OASIS format."""
import json
import sys
from pathlib import Path

def convert_tle_to_oasis(tle_windows_file: Path, output_file: Path):
    """Convert TLE windows to OASIS format."""
    with open(tle_windows_file) as f:
        data = json.load(f)

    # Extract windows and convert format
    tle_windows = data.get('windows', [])

    oasis_windows = []
    for win in tle_windows:
        oasis_win = {
            'type': 'tle',  # TLE-derived window
            'sat': win['satellite'],
            'gw': win['station'],
            'source': 'tle',  # Must be 'log' or 'tle'
            'start': win['start'],
            'end': win['end'],
            'constellation': 'Starlink',
            'elevation_max': win.get('elevation_max', 0),
            'duration_sec': win.get('duration_sec', 0)
        }
        oasis_windows.append(oasis_win)

    # Create OASIS-compatible output
    oasis_data = {
        'meta': {
            'source': 'tle_conversion',
            'count': len(oasis_windows),
            'generated_at': data.get('meta', {}).get('generated_at', ''),
            'stations': data.get('stations', []),
            'satellites': data.get('meta', {}).get('total_satellites', 0)
        },
        'windows': oasis_windows
    }

    with open(output_file, 'w') as f:
        json.dump(oasis_data, f, indent=2)

    print(f"[OK] Converted {len(oasis_windows)} TLE windows to OASIS format")
    print(f"  Output: {output_file}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python convert_tle_to_oasis_format.py <tle_windows.json> <output.json>")
        sys.exit(1)

    convert_tle_to_oasis(Path(sys.argv[1]), Path(sys.argv[2]))
