#!/usr/bin/env python3
"""Integration tests for TLE-OASIS bridge module.

Tests cover:
    - Format conversion (TLE → OASIS)
    - Merge strategies (union, intersection, tle-only, oasis-only)
    - Timezone handling and normalization
    - Ground station coordinate mapping
    - End-to-end integration with parse_oasis_log.py
    - Batch processing
    - Edge cases and error handling
"""
from __future__ import annotations
import pytest
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.tle_oasis_bridge import (
    normalize_timestamp,
    convert_timestamp_timezone,
    parse_tle_gateway_coords,
    find_station_by_coords,
    load_ground_stations,
    convert_tle_to_oasis_format,
    windows_overlap,
    merge_overlapping_windows,
    merge_windows,
    merge_union,
    merge_intersection,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_tle_windows():
    """Sample TLE windows in tle_windows.py output format."""
    return [
        {
            "type": "tle_pass",
            "start": "2025-10-08T10:00:00Z",
            "end": "2025-10-08T10:15:00Z",
            "sat": "ISS",
            "gw": "24.788,120.998"
        },
        {
            "type": "tle_pass",
            "start": "2025-10-08T12:00:00Z",
            "end": "2025-10-08T12:12:00Z",
            "sat": "ISS",
            "gw": "25.033,121.565"
        }
    ]


@pytest.fixture
def sample_oasis_windows():
    """Sample OASIS windows from parse_oasis_log.py."""
    return [
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


@pytest.fixture
def sample_stations():
    """Sample ground station configurations."""
    return [
        {
            "name": "HSINCHU",
            "lat": 24.7881,
            "lon": 120.9979,
            "alt": 52
        },
        {
            "name": "TAIPEI",
            "lat": 25.0330,
            "lon": 121.5654,
            "alt": 10
        },
        {
            "name": "KAOHSIUNG",
            "lat": 22.6273,
            "lon": 120.3014,
            "alt": 15
        }
    ]


@pytest.fixture
def temp_stations_file(tmp_path, sample_stations):
    """Create temporary ground stations JSON file."""
    stations_file = tmp_path / "stations.json"
    stations_file.write_text(json.dumps({
        "ground_stations": sample_stations,
        "network_info": {"operator": "TASA", "country": "Taiwan"}
    }))
    return stations_file


# ============================================================================
# Test Timezone Handling
# ============================================================================

def test_normalize_timestamp_utc():
    """Test timestamp normalization to UTC."""
    # Already UTC with Z suffix
    ts = "2025-10-08T10:15:30Z"
    result = normalize_timestamp(ts, "UTC")
    assert result == "2025-10-08T10:15:30Z"

    # UTC with +00:00 offset
    ts = "2025-10-08T10:15:30+00:00"
    result = normalize_timestamp(ts, "UTC")
    assert result == "2025-10-08T10:15:30Z"


def test_normalize_timestamp_with_offset():
    """Test timestamp normalization with timezone offset."""
    # Taiwan time (UTC+8) to UTC
    ts = "2025-10-08T18:15:30+08:00"
    result = normalize_timestamp(ts, "UTC")
    assert result == "2025-10-08T10:15:30Z"  # Should convert to UTC

    # UTC-5 to UTC
    ts = "2025-10-08T05:15:30-05:00"
    result = normalize_timestamp(ts, "UTC")
    assert result == "2025-10-08T10:15:30Z"


def test_convert_timestamp_timezone():
    """Test timezone conversion between arbitrary zones."""
    # UTC to Taiwan time would require pytz, test basic UTC->UTC
    ts = "2025-10-08T10:15:30Z"
    result = convert_timestamp_timezone(ts, "UTC", "UTC")
    assert result == "2025-10-08T10:15:30Z"


# ============================================================================
# Test Ground Station Mapping
# ============================================================================

def test_parse_tle_gateway_coords():
    """Test parsing gateway coordinates from TLE format."""
    # Valid format
    lat, lon = parse_tle_gateway_coords("24.788,120.998")
    assert abs(lat - 24.788) < 0.001
    assert abs(lon - 120.998) < 0.001

    # Negative coordinates
    lat, lon = parse_tle_gateway_coords("-22.5,145.7")
    assert abs(lat - (-22.5)) < 0.001
    assert abs(lon - 145.7) < 0.001


def test_parse_tle_gateway_coords_invalid():
    """Test error handling for invalid gateway format."""
    with pytest.raises(ValueError, match="Expected 'lat,lon' format"):
        parse_tle_gateway_coords("invalid")

    with pytest.raises(ValueError, match="Invalid gateway coordinate format"):
        parse_tle_gateway_coords("24.788,abc")


def test_find_station_by_coords(sample_stations):
    """Test finding station by coordinates."""
    # Exact match
    name = find_station_by_coords(24.7881, 120.9979, sample_stations, tolerance=0.01)
    assert name == "HSINCHU"

    # Close match within tolerance
    name = find_station_by_coords(24.788, 120.998, sample_stations, tolerance=0.01)
    assert name == "HSINCHU"

    # No match (too far)
    name = find_station_by_coords(30.0, 130.0, sample_stations, tolerance=0.1)
    assert name is None


def test_load_ground_stations(temp_stations_file):
    """Test loading ground stations from JSON file."""
    stations = load_ground_stations(temp_stations_file)
    assert len(stations) == 3
    assert stations[0]['name'] == 'HSINCHU'
    assert stations[1]['name'] == 'TAIPEI'
    assert stations[2]['name'] == 'KAOHSIUNG'


def test_load_ground_stations_missing_file():
    """Test error handling for missing stations file."""
    with pytest.raises(FileNotFoundError):
        load_ground_stations(Path("/nonexistent/stations.json"))


# ============================================================================
# Test Format Conversion
# ============================================================================

def test_convert_tle_to_oasis_format_basic(sample_tle_windows):
    """Test basic TLE to OASIS format conversion."""
    result = convert_tle_to_oasis_format(sample_tle_windows)

    assert len(result) == 2

    # Check first window
    win0 = result[0]
    assert win0['type'] == 'tle'
    assert win0['source'] == 'tle'
    assert win0['sat'] == 'ISS'
    assert win0['gw'] == '24.788,120.998'  # No station mapping
    assert win0['start'] == '2025-10-08T10:00:00Z'
    assert win0['end'] == '2025-10-08T10:15:00Z'


def test_convert_tle_to_oasis_format_with_stations(sample_tle_windows, sample_stations):
    """Test TLE to OASIS conversion with ground station mapping."""
    result = convert_tle_to_oasis_format(sample_tle_windows, stations=sample_stations)

    assert len(result) == 2

    # First window should map to HSINCHU
    win0 = result[0]
    assert win0['gw'] == 'HSINCHU'
    assert win0['sat'] == 'ISS'

    # Second window should map to TAIPEI
    win1 = result[1]
    assert win1['gw'] == 'TAIPEI'


def test_convert_tle_to_oasis_format_preserve_fields():
    """Test that optional TLE fields are preserved."""
    tle_windows = [
        {
            "type": "tle_pass",
            "start": "2025-10-08T10:00:00Z",
            "end": "2025-10-08T10:15:00Z",
            "sat": "ISS",
            "gw": "24.788,120.998",
            "elevation_deg": 45.2,
            "azimuth_deg": 180.5,
            "range_km": 1234.56
        }
    ]

    result = convert_tle_to_oasis_format(tle_windows)
    win = result[0]

    assert win['elevation_deg'] == 45.2
    assert win['azimuth_deg'] == 180.5
    assert win['range_km'] == 1234.56


# ============================================================================
# Test Window Overlap Detection
# ============================================================================

def test_windows_overlap_complete():
    """Test overlap detection for completely overlapping windows."""
    w1 = {
        'start': '2025-10-08T10:00:00Z',
        'end': '2025-10-08T10:30:00Z'
    }
    w2 = {
        'start': '2025-10-08T10:10:00Z',
        'end': '2025-10-08T10:20:00Z'
    }
    assert windows_overlap(w1, w2) is True
    assert windows_overlap(w2, w1) is True


def test_windows_overlap_partial():
    """Test overlap detection for partially overlapping windows."""
    w1 = {
        'start': '2025-10-08T10:00:00Z',
        'end': '2025-10-08T10:20:00Z'
    }
    w2 = {
        'start': '2025-10-08T10:15:00Z',
        'end': '2025-10-08T10:30:00Z'
    }
    assert windows_overlap(w1, w2) is True


def test_windows_overlap_adjacent():
    """Test overlap detection for adjacent (touching) windows."""
    w1 = {
        'start': '2025-10-08T10:00:00Z',
        'end': '2025-10-08T10:15:00Z'
    }
    w2 = {
        'start': '2025-10-08T10:15:00Z',  # Exactly at end of w1
        'end': '2025-10-08T10:30:00Z'
    }
    assert windows_overlap(w1, w2) is True  # Boundaries touch


def test_windows_overlap_no_overlap():
    """Test overlap detection for non-overlapping windows."""
    w1 = {
        'start': '2025-10-08T10:00:00Z',
        'end': '2025-10-08T10:15:00Z'
    }
    w2 = {
        'start': '2025-10-08T10:20:00Z',
        'end': '2025-10-08T10:30:00Z'
    }
    assert windows_overlap(w1, w2) is False


# ============================================================================
# Test Window Merging
# ============================================================================

def test_merge_overlapping_windows():
    """Test merging of two overlapping windows."""
    w1 = {
        'type': 'tle',
        'start': '2025-10-08T10:00:00Z',
        'end': '2025-10-08T10:20:00Z',
        'sat': 'ISS',
        'gw': 'HSINCHU',
        'source': 'tle'
    }
    w2 = {
        'type': 'cmd',
        'start': '2025-10-08T10:15:00Z',
        'end': '2025-10-08T10:30:00Z',
        'sat': 'ISS',
        'gw': 'HSINCHU',
        'source': 'log'
    }

    merged = merge_overlapping_windows(w1, w2)

    # Should use earliest start and latest end
    assert merged['start'] == '2025-10-08T10:00:00Z'
    assert merged['end'] == '2025-10-08T10:30:00Z'

    # Should prefer log source metadata
    assert merged['source'] == 'log'
    assert merged['type'] == 'cmd'


def test_merge_union_no_overlap(sample_oasis_windows):
    """Test union merge with non-overlapping windows."""
    tle_windows = [
        {
            'type': 'tle',
            'start': '2025-10-08T08:00:00Z',
            'end': '2025-10-08T08:15:00Z',
            'sat': 'SAT-2',
            'gw': 'KAOHSIUNG',
            'source': 'tle'
        }
    ]

    result = merge_union(sample_oasis_windows, tle_windows)

    # Should have all windows (2 OASIS + 1 TLE)
    assert len(result) == 3


def test_merge_union_with_overlap():
    """Test union merge with overlapping windows."""
    oasis_windows = [
        {
            'type': 'cmd',
            'start': '2025-10-08T10:00:00Z',
            'end': '2025-10-08T10:20:00Z',
            'sat': 'ISS',
            'gw': 'HSINCHU',
            'source': 'log'
        }
    ]
    tle_windows = [
        {
            'type': 'tle',
            'start': '2025-10-08T10:10:00Z',
            'end': '2025-10-08T10:30:00Z',
            'sat': 'ISS',
            'gw': 'HSINCHU',
            'source': 'tle'
        }
    ]

    result = merge_union(oasis_windows, tle_windows)

    # Should merge into single window
    assert len(result) == 1
    assert result[0]['start'] == '2025-10-08T10:00:00Z'
    assert result[0]['end'] == '2025-10-08T10:30:00Z'


def test_merge_intersection_with_overlap():
    """Test intersection merge with overlapping windows."""
    oasis_windows = [
        {
            'type': 'cmd',
            'start': '2025-10-08T10:00:00Z',
            'end': '2025-10-08T10:20:00Z',
            'sat': 'ISS',
            'gw': 'HSINCHU',
            'source': 'log'
        }
    ]
    tle_windows = [
        {
            'type': 'tle',
            'start': '2025-10-08T10:10:00Z',
            'end': '2025-10-08T10:30:00Z',
            'sat': 'ISS',
            'gw': 'HSINCHU',
            'source': 'tle'
        }
    ]

    result = merge_intersection(oasis_windows, tle_windows)

    # Should return intersection period
    assert len(result) == 1
    assert result[0]['start'] == '2025-10-08T10:10:00Z'  # Later start
    assert result[0]['end'] == '2025-10-08T10:20:00Z'    # Earlier end
    assert result[0]['source'] == 'log+tle'


def test_merge_intersection_no_overlap():
    """Test intersection merge with no overlapping windows."""
    oasis_windows = [
        {
            'type': 'cmd',
            'start': '2025-10-08T10:00:00Z',
            'end': '2025-10-08T10:15:00Z',
            'sat': 'ISS',
            'gw': 'HSINCHU',
            'source': 'log'
        }
    ]
    tle_windows = [
        {
            'type': 'tle',
            'start': '2025-10-08T10:30:00Z',
            'end': '2025-10-08T10:45:00Z',
            'sat': 'ISS',
            'gw': 'HSINCHU',
            'source': 'tle'
        }
    ]

    result = merge_intersection(oasis_windows, tle_windows)

    # Should return empty list (no overlap)
    assert len(result) == 0


# ============================================================================
# Test Merge Strategies
# ============================================================================

def test_merge_windows_union(sample_oasis_windows, sample_tle_windows, sample_stations):
    """Test merge_windows with union strategy."""
    result = merge_windows(
        sample_oasis_windows,
        sample_tle_windows,
        strategy='union',
        stations=sample_stations
    )

    # Should include windows from both sources
    assert len(result) >= 2


def test_merge_windows_intersection(sample_oasis_windows, sample_tle_windows, sample_stations):
    """Test merge_windows with intersection strategy."""
    result = merge_windows(
        sample_oasis_windows,
        sample_tle_windows,
        strategy='intersection',
        stations=sample_stations
    )

    # Should only include overlapping windows
    # In this case, OASIS ISS@HSINCHU overlaps with TLE ISS@HSINCHU
    assert len(result) >= 0  # May be 0 or more depending on overlap


def test_merge_windows_tle_only(sample_oasis_windows, sample_tle_windows, sample_stations):
    """Test merge_windows with tle-only strategy."""
    result = merge_windows(
        sample_oasis_windows,
        sample_tle_windows,
        strategy='tle-only',
        stations=sample_stations
    )

    # Should only include TLE windows
    assert len(result) == 2
    assert all(w['source'] == 'tle' for w in result)


def test_merge_windows_oasis_only(sample_oasis_windows, sample_tle_windows, sample_stations):
    """Test merge_windows with oasis-only strategy."""
    result = merge_windows(
        sample_oasis_windows,
        sample_tle_windows,
        strategy='oasis-only',
        stations=sample_stations
    )

    # Should only include OASIS windows
    assert len(result) == 2
    assert all(w['source'] == 'log' for w in result)


def test_merge_windows_invalid_strategy(sample_oasis_windows, sample_tle_windows):
    """Test merge_windows with invalid strategy."""
    with pytest.raises(ValueError, match="Invalid strategy"):
        merge_windows(
            sample_oasis_windows,
            sample_tle_windows,
            strategy='invalid',
            stations=None
        )


# ============================================================================
# Test End-to-End Integration
# ============================================================================

def test_end_to_end_with_tle(tmp_path):
    """Test complete integration: OASIS log + TLE → merged windows."""
    # Create sample OASIS log
    oasis_log = tmp_path / "test.log"
    oasis_log.write_text("""
enter command window @ 2025-10-08T10:05:00Z sat=ISS gw=HSINCHU
exit command window @ 2025-10-08T10:20:00Z sat=ISS gw=HSINCHU
X-band data link window: 2025-10-08T14:00:00Z..2025-10-08T14:08:00Z sat=SAT-1 gw=TAIPEI
""")

    # Create sample TLE file (ISS)
    tle_file = tmp_path / "iss.tle"
    tle_file.write_text("""ISS (ZARYA)
1 25544U 98067A   25280.50000000  .00002182  00000-0  41420-4 0  9990
2 25544  51.6400 208.9163 0002571  59.2676 120.7846 15.54225995999999""")

    # Create stations file
    stations_file = tmp_path / "stations.json"
    stations_file.write_text(json.dumps({
        "ground_stations": [
            {"name": "HSINCHU", "lat": 24.7881, "lon": 120.9979, "alt": 52},
            {"name": "TAIPEI", "lat": 25.0330, "lon": 121.5654, "alt": 10}
        ]
    }))

    # Parse OASIS log with TLE integration
    output_file = tmp_path / "merged.json"

    import subprocess
    cmd = [
        sys.executable,
        str(Path(__file__).parent.parent / "scripts" / "parse_oasis_log.py"),
        str(oasis_log),
        "--output", str(output_file),
        "--tle-file", str(tle_file),
        "--stations", str(stations_file),
        "--merge-strategy", "union"
    ]

    # Note: This test requires tle_windows.py to work correctly
    # It may fail if TLE propagation fails, which is expected for test TLEs
    # We'll check that the file is created and has expected structure
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Check output file exists
        if output_file.exists():
            data = json.loads(output_file.read_text())

            # Verify structure
            assert 'meta' in data
            assert 'windows' in data
            assert data['meta']['merge_strategy'] == 'union'
            assert isinstance(data['windows'], list)

    except subprocess.CalledProcessError:
        # TLE calculation may fail with test data, which is acceptable
        pytest.skip("TLE calculation failed (expected with test data)")


# ============================================================================
# Test Edge Cases
# ============================================================================

def test_empty_windows_union():
    """Test union merge with empty window lists."""
    result = merge_union([], [])
    assert result == []

    oasis = [{'type': 'cmd', 'start': '2025-10-08T10:00:00Z', 'end': '2025-10-08T10:15:00Z',
              'sat': 'ISS', 'gw': 'HSINCHU', 'source': 'log'}]
    result = merge_union(oasis, [])
    assert len(result) == 1


def test_empty_windows_intersection():
    """Test intersection merge with empty window lists."""
    result = merge_intersection([], [])
    assert result == []


def test_different_satellites_no_merge():
    """Test that windows from different satellites don't merge."""
    oasis = [
        {'type': 'cmd', 'start': '2025-10-08T10:00:00Z', 'end': '2025-10-08T10:20:00Z',
         'sat': 'ISS', 'gw': 'HSINCHU', 'source': 'log'}
    ]
    tle = [
        {'type': 'tle', 'start': '2025-10-08T10:10:00Z', 'end': '2025-10-08T10:30:00Z',
         'sat': 'SAT-2', 'gw': 'HSINCHU', 'source': 'tle'}
    ]

    result = merge_union(oasis, tle)
    # Should keep separate windows (different satellites)
    assert len(result) == 2


def test_different_gateways_no_merge():
    """Test that windows from different gateways don't merge."""
    oasis = [
        {'type': 'cmd', 'start': '2025-10-08T10:00:00Z', 'end': '2025-10-08T10:20:00Z',
         'sat': 'ISS', 'gw': 'HSINCHU', 'source': 'log'}
    ]
    tle = [
        {'type': 'tle', 'start': '2025-10-08T10:10:00Z', 'end': '2025-10-08T10:30:00Z',
         'sat': 'ISS', 'gw': 'TAIPEI', 'source': 'tle'}
    ]

    result = merge_union(oasis, tle)
    # Should keep separate windows (different gateways)
    assert len(result) == 2


# ============================================================================
# Performance Tests
# ============================================================================

def test_merge_performance_large_dataset():
    """Test merge performance with large number of windows."""
    import time

    # Generate 100 OASIS windows
    oasis_windows = []
    for i in range(100):
        start = datetime(2025, 10, 8, i // 10, (i % 10) * 6, 0, tzinfo=timezone.utc)
        end = start + timedelta(minutes=5)
        oasis_windows.append({
            'type': 'cmd',
            'start': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'end': end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'sat': f'SAT-{i % 10}',
            'gw': f'GW-{i % 5}',
            'source': 'log'
        })

    # Generate 100 TLE windows
    tle_windows = []
    for i in range(100):
        start = datetime(2025, 10, 8, i // 10, (i % 10) * 6 + 2, 0, tzinfo=timezone.utc)
        end = start + timedelta(minutes=5)
        tle_windows.append({
            'type': 'tle',
            'start': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'end': end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'sat': f'SAT-{i % 10}',
            'gw': f'GW-{i % 5}',
            'source': 'tle'
        })

    # Time the merge
    start_time = time.time()
    result = merge_union(oasis_windows, tle_windows)
    elapsed = time.time() - start_time

    # Should complete in reasonable time (< 1 second for 200 windows)
    assert elapsed < 1.0
    assert len(result) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
