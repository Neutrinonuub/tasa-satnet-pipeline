#!/usr/bin/env python3
"""Convert multi-constellation TLE windows to OASIS format with constellation metadata."""
import json
import sys
from pathlib import Path

# Constellation metadata
CONSTELLATION_CONFIG = {
    'GPS': {
        'priority': 'high',
        'frequency_band': 'L-band',
        'processing_delay_ms': 2.0
    },
    'IRIDIUM': {
        'priority': 'medium',
        'frequency_band': 'Ka-band',
        'processing_delay_ms': 5.0
    },
    'ONEWEB': {
        'priority': 'low',
        'frequency_band': 'Ku-band',
        'processing_delay_ms': 8.0
    },
    'STARLINK': {
        'priority': 'low',
        'frequency_band': 'Ka-band',
        'processing_delay_ms': 8.0
    }
}

def detect_constellation(satellite_name: str) -> str:
    """Detect constellation from satellite name."""
    name_upper = satellite_name.upper()
    if 'GPS' in name_upper:
        return 'GPS'
    elif 'IRIDIUM' in name_upper:
        return 'Iridium'
    elif 'ONEWEB' in name_upper:
        return 'OneWeb'
    elif 'STARLINK' in name_upper:
        return 'Starlink'
    else:
        return 'Unknown'

def convert_multi_const_to_oasis(tle_windows_file: Path, output_file: Path):
    """Convert multi-constellation TLE windows to OASIS format."""
    with open(tle_windows_file) as f:
        data = json.load(f)

    # Extract windows and convert format
    tle_windows = data.get('windows', [])

    oasis_windows = []
    constellation_counts = {}

    for win in tle_windows:
        satellite_name = win['satellite']
        constellation = detect_constellation(satellite_name)

        # Track constellation counts
        constellation_counts[constellation] = constellation_counts.get(constellation, 0) + 1

        # Get constellation config
        const_key = constellation.upper()
        config = CONSTELLATION_CONFIG.get(const_key, {
            'priority': 'low',
            'frequency_band': 'Unknown',
            'processing_delay_ms': 10.0
        })

        oasis_win = {
            'type': 'tle',
            'sat': satellite_name,
            'gw': win['station'],
            'source': 'tle',
            'start': win['start'],
            'end': win['end'],
            'constellation': constellation,
            'priority': config['priority'],
            'frequency_band': config['frequency_band'],
            'processing_delay_ms': config['processing_delay_ms'],
            'elevation_max': win.get('elevation_max', 0),
            'duration_sec': win.get('duration_sec', 0)
        }
        oasis_windows.append(oasis_win)

    # Create OASIS-compatible output
    oasis_data = {
        'meta': {
            'source': 'multi_constellation',
            'count': len(oasis_windows),
            'generated_at': data.get('meta', {}).get('generated_at', ''),
            'stations': data.get('stations', []),
            'satellites': data.get('meta', {}).get('total_satellites', 0),
            'constellations': list(constellation_counts.keys()),
            'constellation_distribution': constellation_counts
        },
        'windows': oasis_windows
    }

    with open(output_file, 'w') as f:
        json.dump(oasis_data, f, indent=2)

    print(f"[OK] Converted {len(oasis_windows)} multi-constellation windows to OASIS format")
    print(f"  Constellations: {', '.join(f'{k} ({v})' for k, v in constellation_counts.items())}")
    print(f"  Output: {output_file}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python convert_multi_const_to_oasis.py <multi_const_windows.json> <output.json>")
        sys.exit(1)

    convert_multi_const_to_oasis(Path(sys.argv[1]), Path(sys.argv[2]))
