#!/usr/bin/env python3
"""TLE-OASIS Bridge Module.

This module provides seamless integration between TLE-based satellite visibility
windows and OASIS log parsing. It handles timezone conversions, format conversions,
and various merge strategies.

Usage:
    from tle_oasis_bridge import convert_tle_to_oasis_format, merge_windows

    # Convert TLE windows to OASIS format
    oasis_windows = convert_tle_to_oasis_format(tle_windows)

    # Merge TLE and OASIS windows
    merged = merge_windows(oasis_windows, tle_windows, strategy='union')

Features:
    - Convert TLE window format to OASIS window format
    - Handle timezone conversions (UTC <-> local time)
    - Multiple merge strategies: union, intersection, tle-only, oasis-only
    - Support for batch processing multiple satellites
    - Ground station name mapping (lat/lon to station names)
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.schemas import validate_window_item, ValidationError

# Type aliases
MergeStrategy = Literal['union', 'intersection', 'tle-only', 'oasis-only']
WindowList = List[Dict[str, Any]]


# ============================================================================
# Timezone Handling
# ============================================================================

def normalize_timestamp(ts: str, target_tz: str = "UTC") -> str:
    """Normalize timestamp to target timezone.

    Args:
        ts: Timestamp string in ISO 8601 format (e.g., "2025-10-08T10:15:30Z")
        target_tz: Target timezone (default: "UTC")

    Returns:
        Normalized timestamp in ISO 8601 format

    Examples:
        >>> normalize_timestamp("2025-10-08T10:15:30Z", "UTC")
        '2025-10-08T10:15:30Z'
        >>> normalize_timestamp("2025-10-08T18:15:30+08:00", "UTC")
        '2025-10-08T10:15:30Z'
    """
    # Parse timestamp (handle both Z and +HH:MM formats)
    if ts.endswith('Z'):
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    else:
        dt = datetime.fromisoformat(ts)

    # Convert to target timezone
    if target_tz == "UTC":
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        # For non-UTC timezones, require pytz
        try:
            import pytz
            tz = pytz.timezone(target_tz)
            dt_local = dt.astimezone(tz)
            return dt_local.isoformat()
        except ImportError:
            import warnings
            warnings.warn(f"pytz not available, returning UTC instead of {target_tz}")
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def convert_timestamp_timezone(ts: str, from_tz: str, to_tz: str) -> str:
    """Convert timestamp from one timezone to another.

    Args:
        ts: Timestamp string
        from_tz: Source timezone name (e.g., "Asia/Taipei", "UTC")
        to_tz: Target timezone name

    Returns:
        Converted timestamp string
    """
    # First normalize to ensure proper format
    normalized = normalize_timestamp(ts, from_tz)
    # Then convert to target timezone
    return normalize_timestamp(normalized, to_tz)


# ============================================================================
# Ground Station Mapping
# ============================================================================

def load_ground_stations(stations_file: Path) -> List[Dict[str, Any]]:
    """Load ground station configurations from JSON file.

    Args:
        stations_file: Path to taiwan_ground_stations.json or similar

    Returns:
        List of ground station configurations

    Raises:
        FileNotFoundError: If stations file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    if not stations_file.exists():
        raise FileNotFoundError(f"Ground stations file not found: {stations_file}")

    data = json.loads(stations_file.read_text(encoding='utf-8'))
    return data.get('ground_stations', [])


def find_station_by_coords(lat: float, lon: float,
                          stations: List[Dict[str, Any]],
                          tolerance: float = 0.1) -> Optional[str]:
    """Find ground station name by coordinates.

    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        stations: List of ground station configurations
        tolerance: Maximum distance in degrees to consider a match

    Returns:
        Station name if found, None otherwise

    Examples:
        >>> stations = [{'name': 'HSINCHU', 'lat': 24.7881, 'lon': 120.9979}]
        >>> find_station_by_coords(24.788, 120.998, stations, tolerance=0.01)
        'HSINCHU'
    """
    import math

    for station in stations:
        station_lat = station.get('lat', 0)
        station_lon = station.get('lon', 0)

        # Calculate Euclidean distance in degrees
        dist = math.sqrt((lat - station_lat)**2 + (lon - station_lon)**2)

        if dist <= tolerance:
            return station['name']

    return None


def parse_tle_gateway_coords(gw_str: str) -> tuple[float, float]:
    """Parse gateway string from TLE format (lat,lon) to coordinates.

    Args:
        gw_str: Gateway string in format "lat,lon" (e.g., "24.788,120.998")

    Returns:
        Tuple of (latitude, longitude) in degrees

    Raises:
        ValueError: If gateway string format is invalid

    Examples:
        >>> parse_tle_gateway_coords("24.788,120.998")
        (24.788, 120.998)
    """
    try:
        parts = gw_str.split(',')
        if len(parts) != 2:
            raise ValueError(f"Expected 'lat,lon' format, got: {gw_str}")
        return float(parts[0]), float(parts[1])
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid gateway coordinate format '{gw_str}': {e}")


# ============================================================================
# Format Conversion
# ============================================================================

def convert_tle_to_oasis_format(tle_windows: WindowList,
                                stations: Optional[List[Dict[str, Any]]] = None,
                                window_type: str = "tle") -> WindowList:
    """Convert TLE-derived windows to OASIS window format.

    Args:
        tle_windows: List of TLE windows from tle_windows.py output
        stations: Optional list of ground station configs for name mapping
        window_type: Window type to assign (default: "tle")

    Returns:
        List of windows in OASIS format with proper structure

    Input format (TLE):
        {
            "type": "tle_pass",
            "start": "2025-10-08T10:15:30Z",
            "end": "2025-10-08T10:25:30Z",
            "sat": "ISS",
            "gw": "24.788,120.998"
        }

    Output format (OASIS):
        {
            "type": "tle",
            "start": "2025-10-08T10:15:30Z",
            "end": "2025-10-08T10:25:30Z",
            "sat": "ISS",
            "gw": "HSINCHU",
            "source": "tle"
        }
    """
    oasis_windows = []

    for tle_win in tle_windows:
        # Normalize timestamps to UTC
        start_utc = normalize_timestamp(tle_win['start'], 'UTC')
        end_utc = normalize_timestamp(tle_win['end'], 'UTC')

        # Convert gateway coordinates to station name if possible
        gw_str = tle_win['gw']
        if stations and ',' in gw_str:
            try:
                lat, lon = parse_tle_gateway_coords(gw_str)
                station_name = find_station_by_coords(lat, lon, stations)
                if station_name:
                    gw_str = station_name
            except ValueError:
                # Keep original format if parsing fails
                pass

        # Build OASIS-compatible window
        oasis_win = {
            'type': window_type,
            'start': start_utc,
            'end': end_utc,
            'sat': tle_win['sat'],
            'gw': gw_str,
            'source': 'tle'
        }

        # Preserve optional fields from TLE windows
        for field in ['elevation_deg', 'azimuth_deg', 'range_km']:
            if field in tle_win:
                oasis_win[field] = tle_win[field]

        oasis_windows.append(oasis_win)

    return oasis_windows


# ============================================================================
# Window Merging
# ============================================================================

def windows_overlap(w1: Dict[str, Any], w2: Dict[str, Any]) -> bool:
    """Check if two windows overlap in time.

    Args:
        w1, w2: Window dictionaries with 'start' and 'end' timestamps

    Returns:
        True if windows overlap, False otherwise

    Examples:
        >>> w1 = {'start': '2025-10-08T10:00:00Z', 'end': '2025-10-08T10:30:00Z'}
        >>> w2 = {'start': '2025-10-08T10:20:00Z', 'end': '2025-10-08T10:50:00Z'}
        >>> windows_overlap(w1, w2)
        True
    """
    start1 = datetime.fromisoformat(w1['start'].replace('Z', '+00:00'))
    end1 = datetime.fromisoformat(w1['end'].replace('Z', '+00:00'))
    start2 = datetime.fromisoformat(w2['start'].replace('Z', '+00:00'))
    end2 = datetime.fromisoformat(w2['end'].replace('Z', '+00:00'))

    # Check for overlap: (start1 <= end2) AND (start2 <= end1)
    return start1 <= end2 and start2 <= end1


def merge_overlapping_windows(w1: Dict[str, Any], w2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two overlapping windows into one.

    Args:
        w1, w2: Overlapping window dictionaries

    Returns:
        Merged window with earliest start and latest end

    Examples:
        >>> w1 = {'start': '2025-10-08T10:00:00Z', 'end': '2025-10-08T10:30:00Z',
        ...       'sat': 'SAT-1', 'gw': 'HSINCHU', 'type': 'tle', 'source': 'tle'}
        >>> w2 = {'start': '2025-10-08T10:20:00Z', 'end': '2025-10-08T10:50:00Z',
        ...       'sat': 'SAT-1', 'gw': 'HSINCHU', 'type': 'cmd', 'source': 'log'}
        >>> merged = merge_overlapping_windows(w1, w2)
        >>> merged['start']
        '2025-10-08T10:00:00Z'
        >>> merged['end']
        '2025-10-08T10:50:00Z'
    """
    start1 = datetime.fromisoformat(w1['start'].replace('Z', '+00:00'))
    end1 = datetime.fromisoformat(w1['end'].replace('Z', '+00:00'))
    start2 = datetime.fromisoformat(w2['start'].replace('Z', '+00:00'))
    end2 = datetime.fromisoformat(w2['end'].replace('Z', '+00:00'))

    # Use earliest start and latest end
    merged_start = min(start1, start2)
    merged_end = max(end1, end2)

    # Prefer OASIS log metadata over TLE
    merged = w1.copy()
    if w2.get('source') == 'log':
        merged.update({
            'type': w2['type'],
            'source': 'log'  # Prefer log source
        })

    merged['start'] = merged_start.strftime('%Y-%m-%dT%H:%M:%SZ')
    merged['end'] = merged_end.strftime('%Y-%m-%dT%H:%M:%SZ')

    return merged


def merge_windows(oasis_windows: WindowList,
                 tle_windows: WindowList,
                 strategy: MergeStrategy = 'union',
                 stations: Optional[List[Dict[str, Any]]] = None) -> WindowList:
    """Merge OASIS and TLE windows using specified strategy.

    Args:
        oasis_windows: Windows from OASIS log parsing
        tle_windows: Windows from TLE calculations
        strategy: Merge strategy - one of:
            - 'union': All windows from both sources (deduplicated)
            - 'intersection': Only overlapping windows
            - 'tle-only': Use only TLE windows
            - 'oasis-only': Use only OASIS windows
        stations: Optional ground station configs for coordinate mapping

    Returns:
        Merged window list according to strategy

    Raises:
        ValueError: If strategy is invalid
    """
    valid_strategies: List[MergeStrategy] = ['union', 'intersection', 'tle-only', 'oasis-only']
    if strategy not in valid_strategies:
        raise ValueError(f"Invalid strategy '{strategy}'. Must be one of: {valid_strategies}")

    # Convert TLE windows to OASIS format first
    tle_converted = convert_tle_to_oasis_format(tle_windows, stations)

    if strategy == 'tle-only':
        return tle_converted
    elif strategy == 'oasis-only':
        return oasis_windows
    elif strategy == 'union':
        return merge_union(oasis_windows, tle_converted)
    elif strategy == 'intersection':
        return merge_intersection(oasis_windows, tle_converted)

    return []  # Should never reach here


def merge_union(oasis_windows: WindowList, tle_windows: WindowList) -> WindowList:
    """Union merge: all windows from both sources, deduplicated.

    Deduplication logic:
        - If windows overlap AND have same sat/gw, merge them
        - Prefer OASIS log metadata for merged windows
        - Keep all non-overlapping windows

    Args:
        oasis_windows: OASIS log windows
        tle_windows: TLE-derived windows (already converted to OASIS format)

    Returns:
        Merged window list
    """
    merged = oasis_windows.copy()

    for tle_win in tle_windows:
        # Check if this TLE window overlaps with any OASIS window
        merged_with_existing = False

        for i, oasis_win in enumerate(merged):
            # Check if same satellite and gateway
            if (tle_win['sat'] == oasis_win['sat'] and
                tle_win['gw'] == oasis_win['gw'] and
                windows_overlap(tle_win, oasis_win)):
                # Merge overlapping windows
                merged[i] = merge_overlapping_windows(oasis_win, tle_win)
                merged_with_existing = True
                break

        # If no overlap found, add as new window
        if not merged_with_existing:
            merged.append(tle_win)

    return merged


def merge_intersection(oasis_windows: WindowList, tle_windows: WindowList) -> WindowList:
    """Intersection merge: only overlapping windows.

    Returns windows that exist in BOTH OASIS and TLE sources.

    Args:
        oasis_windows: OASIS log windows
        tle_windows: TLE-derived windows (already converted to OASIS format)

    Returns:
        List of overlapping windows
    """
    intersections = []

    for oasis_win in oasis_windows:
        for tle_win in tle_windows:
            # Check if same satellite and gateway
            if (oasis_win['sat'] == tle_win['sat'] and
                oasis_win['gw'] == tle_win['gw'] and
                windows_overlap(oasis_win, tle_win)):
                # Create intersection window (use overlap period)
                start_oasis = datetime.fromisoformat(oasis_win['start'].replace('Z', '+00:00'))
                end_oasis = datetime.fromisoformat(oasis_win['end'].replace('Z', '+00:00'))
                start_tle = datetime.fromisoformat(tle_win['start'].replace('Z', '+00:00'))
                end_tle = datetime.fromisoformat(tle_win['end'].replace('Z', '+00:00'))

                # Intersection period
                intersect_start = max(start_oasis, start_tle)
                intersect_end = min(end_oasis, end_tle)

                intersect_win = oasis_win.copy()
                intersect_win['start'] = intersect_start.strftime('%Y-%m-%dT%H:%M:%SZ')
                intersect_win['end'] = intersect_end.strftime('%Y-%m-%dT%H:%M:%SZ')
                intersect_win['source'] = 'log+tle'  # Mark as verified by both sources

                intersections.append(intersect_win)

    return intersections


# ============================================================================
# Batch Processing
# ============================================================================

def process_batch_tle_files(tle_files: List[Path],
                           stations_file: Path,
                           start_time: str,
                           end_time: str,
                           min_elevation: float = 10.0) -> Dict[str, WindowList]:
    """Process multiple TLE files and generate windows for each satellite.

    Args:
        tle_files: List of TLE file paths
        stations_file: Path to ground stations JSON
        start_time: Start time for window calculation (ISO 8601)
        end_time: End time for window calculation (ISO 8601)
        min_elevation: Minimum elevation angle in degrees

    Returns:
        Dictionary mapping satellite name to list of windows

    Example:
        >>> tle_files = [Path('data/iss.tle'), Path('data/starlink.tle')]
        >>> windows = process_batch_tle_files(tle_files, Path('data/stations.json'),
        ...                                   '2025-10-08T00:00:00Z', '2025-10-09T00:00:00Z')
        >>> windows.keys()
        dict_keys(['ISS', 'STARLINK-1234', ...])
    """
    import subprocess

    stations = load_ground_stations(stations_file)
    all_windows = {}

    for tle_file in tle_files:
        for station in stations:
            # Run tle_windows.py for each TLE + station combination
            cmd = [
                sys.executable,
                str(Path(__file__).parent / 'tle_windows.py'),
                '--tle', str(tle_file),
                '--lat', str(station['lat']),
                '--lon', str(station['lon']),
                '--alt', str(station.get('alt', 0.0)),
                '--start', start_time,
                '--end', end_time,
                '--min-elev', str(min_elevation),
                '--out', '/tmp/tle_temp.json'
            ]

            try:
                subprocess.run(cmd, check=True, capture_output=True)
                result = json.loads(Path('/tmp/tle_temp.json').read_text())

                for window in result['windows']:
                    sat_name = window['sat']
                    if sat_name not in all_windows:
                        all_windows[sat_name] = []
                    all_windows[sat_name].append(window)

            except subprocess.CalledProcessError:
                # Skip failed TLE processing
                continue

    return all_windows


# ============================================================================
# Main Entry Point (for testing)
# ============================================================================

def main():
    """CLI interface for testing the bridge module."""
    import argparse

    parser = argparse.ArgumentParser(description='TLE-OASIS Bridge Utility')
    parser.add_argument('--tle-windows', type=Path, help='TLE windows JSON file')
    parser.add_argument('--oasis-windows', type=Path, help='OASIS windows JSON file')
    parser.add_argument('--stations', type=Path, help='Ground stations JSON file')
    parser.add_argument('--strategy', type=str, default='union',
                       choices=['union', 'intersection', 'tle-only', 'oasis-only'])
    parser.add_argument('--output', type=Path, default=Path('data/merged_windows.json'))

    args = parser.parse_args()

    # Load input files
    tle_data = json.loads(args.tle_windows.read_text()) if args.tle_windows else {'windows': []}
    oasis_data = json.loads(args.oasis_windows.read_text()) if args.oasis_windows else {'windows': []}
    stations = load_ground_stations(args.stations) if args.stations else None

    # Merge windows
    merged = merge_windows(
        oasis_data['windows'],
        tle_data['windows'],
        strategy=args.strategy,
        stations=stations
    )

    # Output result
    output = {
        'meta': {
            'strategy': args.strategy,
            'tle_source': str(args.tle_windows) if args.tle_windows else 'none',
            'oasis_source': str(args.oasis_windows) if args.oasis_windows else 'none',
            'count': len(merged)
        },
        'windows': merged
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(f"Merged {len(merged)} windows using '{args.strategy}' strategy")
    print(f"Output saved to: {args.output}")


if __name__ == '__main__':
    main()
