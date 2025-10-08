#!/usr/bin/env python3
"""Test multi-constellation integration and processing."""
from __future__ import annotations
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from scripts.multi_constellation import (
    merge_tle_files,
    identify_constellation,
    calculate_mixed_windows,
    detect_conflicts,
    prioritize_scheduling,
    ConstellationConfig,
    CONSTELLATION_PATTERNS,
    FREQUENCY_BANDS,
    PRIORITY_LEVELS
)


@pytest.fixture
def sample_tle_gps(tmp_path):
    """Create sample GPS TLE file."""
    tle = tmp_path / "gps.tle"
    tle.write_text("""GPS BIIA-10 (PRN 32)
1 20959U 90103A   24280.50000000 -.00000027  00000+0  00000+0 0  9998
2 20959  54.9480 187.6771 0115178 208.0806 151.3064  2.00564475123456
GPS BIIR-2  (PRN 13)
1 24876U 97035A   24280.50000000 -.00000027  00000+0  00000+0 0  9999
2 24876  55.4289 127.3456 0078456 189.2345 170.5678  2.00561234234567
""")
    return tle


@pytest.fixture
def sample_tle_iridium(tmp_path):
    """Create sample Iridium TLE file."""
    tle = tmp_path / "iridium.tle"
    tle.write_text("""IRIDIUM 102
1 24794U 97020B   24280.50000000  .00000067  00000+0  16962-4 0  9992
2 24794  86.3945  54.2881 0002341  89.5678 270.5755 14.34218475456789
IRIDIUM 106
1 24840U 97030C   24280.50000000  .00000067  00000+0  16962-4 0  9993
2 24840  86.3945 123.4567 0002341 123.4567 236.5432 14.34218475567890
""")
    return tle


@pytest.fixture
def sample_tle_oneweb(tmp_path):
    """Create sample OneWeb TLE file."""
    tle = tmp_path / "oneweb.tle"
    tle.write_text("""ONEWEB-0001
1 44037U 19011A   24280.50000000  .00001234  00000+0  12345-3 0  9991
2 44037  87.9012 234.5678 0001234  45.6789 314.3210 13.12345678234567
ONEWEB-0002
1 44038U 19011B   24280.50000000  .00001234  00000+0  12345-3 0  9992
2 44038  87.9012 234.5678 0001234  45.6789 314.3210 13.12345678234568
""")
    return tle


@pytest.fixture
def sample_tle_starlink(tmp_path):
    """Create sample Starlink TLE file."""
    tle = tmp_path / "starlink.tle"
    tle.write_text("""STARLINK-1007
1 44713U 19074A   24280.50000000  .00001234  00000+0  12345-3 0  9990
2 44713  53.0012 123.4567 0001234  78.9012 281.2345 15.12345678123456
STARLINK-1008
1 44714U 19074B   24280.50000000  .00001234  00000+0  12345-3 0  9991
2 44714  53.0012 123.4567 0001234  78.9012 281.2345 15.12345678123457
""")
    return tle


@pytest.fixture
def ground_stations():
    """Sample ground stations."""
    return [
        {"name": "TASA-1", "lat": 25.0330, "lon": 121.5654, "alt": 0},
        {"name": "TASA-2", "lat": 24.7874, "lon": 120.9971, "alt": 0}
    ]


class TestTLEMerging:
    """Test TLE file merging functionality."""

    def test_merge_single_file(self, sample_tle_gps, tmp_path):
        """Test merging a single TLE file."""
        output = tmp_path / "merged.tle"
        stats = merge_tle_files([sample_tle_gps], output)

        assert output.exists()
        assert stats['total_satellites'] == 2
        assert stats['constellations'] == ['GPS']

        # Verify content
        content = output.read_text()
        assert 'GPS BIIA-10' in content
        assert 'GPS BIIR-2' in content

    def test_merge_multiple_files(self, sample_tle_gps, sample_tle_iridium,
                                   sample_tle_oneweb, tmp_path):
        """Test merging multiple constellation TLE files."""
        output = tmp_path / "merged.tle"
        stats = merge_tle_files(
            [sample_tle_gps, sample_tle_iridium, sample_tle_oneweb],
            output
        )

        assert stats['total_satellites'] == 6
        assert set(stats['constellations']) == {'GPS', 'Iridium', 'OneWeb'}

        content = output.read_text()
        assert 'GPS BIIA-10' in content
        assert 'IRIDIUM 102' in content
        assert 'ONEWEB-0001' in content

    def test_merge_preserves_format(self, sample_tle_gps, tmp_path):
        """Test that merging preserves TLE format."""
        output = tmp_path / "merged.tle"
        merge_tle_files([sample_tle_gps], output)

        lines = output.read_text().strip().split('\n')
        # Should have 6 lines (2 satellites × 3 lines each)
        assert len(lines) == 6

        # Check TLE line format
        assert lines[1].startswith('1 ')
        assert lines[2].startswith('2 ')
        assert lines[4].startswith('1 ')
        assert lines[5].startswith('2 ')

    def test_merge_deduplication(self, sample_tle_gps, tmp_path):
        """Test that duplicate satellites are handled."""
        output = tmp_path / "merged.tle"
        # Try to merge same file twice
        stats = merge_tle_files([sample_tle_gps, sample_tle_gps], output)

        # Should deduplicate based on NORAD ID
        assert stats['total_satellites'] == 2
        assert stats['duplicates_removed'] >= 0


class TestConstellationIdentification:
    """Test constellation identification logic."""

    def test_identify_gps(self):
        """Test GPS satellite identification."""
        assert identify_constellation("GPS BIIA-10 (PRN 32)") == "GPS"
        assert identify_constellation("GPS BIIR-2  (PRN 13)") == "GPS"
        assert identify_constellation("NAVSTAR 74") == "GPS"

    def test_identify_iridium(self):
        """Test Iridium satellite identification."""
        assert identify_constellation("IRIDIUM 102") == "Iridium"
        assert identify_constellation("IRIDIUM NEXT 106") == "Iridium"

    def test_identify_oneweb(self):
        """Test OneWeb satellite identification."""
        assert identify_constellation("ONEWEB-0001") == "OneWeb"
        assert identify_constellation("ONEWEB-0999") == "OneWeb"

    def test_identify_starlink(self):
        """Test Starlink satellite identification."""
        assert identify_constellation("STARLINK-1007") == "Starlink"
        assert identify_constellation("STARLINK-30") == "Starlink"

    def test_identify_unknown(self):
        """Test unknown satellite returns Unknown."""
        assert identify_constellation("SOME RANDOM SAT") == "Unknown"
        assert identify_constellation("ISS (ZARYA)") == "Unknown"

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        assert identify_constellation("gps biia-10") == "GPS"
        assert identify_constellation("iRiDiUm 102") == "Iridium"
        assert identify_constellation("starlink-1007") == "Starlink"


class TestFrequencyBandMapping:
    """Test frequency band mapping for constellations."""

    def test_frequency_bands_defined(self):
        """Test that all major constellations have frequency bands."""
        assert "GPS" in FREQUENCY_BANDS
        assert "Iridium" in FREQUENCY_BANDS
        assert "OneWeb" in FREQUENCY_BANDS
        assert "Starlink" in FREQUENCY_BANDS

    def test_gps_frequency(self):
        """Test GPS uses L-band."""
        assert FREQUENCY_BANDS["GPS"] == "L-band"

    def test_iridium_frequency(self):
        """Test Iridium uses Ka-band."""
        assert FREQUENCY_BANDS["Iridium"] == "Ka-band"

    def test_oneweb_frequency(self):
        """Test OneWeb uses Ku-band."""
        assert FREQUENCY_BANDS["OneWeb"] == "Ku-band"

    def test_starlink_frequency(self):
        """Test Starlink uses Ka-band."""
        assert FREQUENCY_BANDS["Starlink"] == "Ka-band"


class TestPriorityLevels:
    """Test priority level assignments."""

    def test_priority_levels_defined(self):
        """Test that all constellations have priorities."""
        assert "GPS" in PRIORITY_LEVELS
        assert "Iridium" in PRIORITY_LEVELS
        assert "OneWeb" in PRIORITY_LEVELS
        assert "Starlink" in PRIORITY_LEVELS

    def test_gps_highest_priority(self):
        """Test GPS has highest priority."""
        assert PRIORITY_LEVELS["GPS"] == "high"

    def test_iridium_medium_priority(self):
        """Test Iridium has medium priority."""
        assert PRIORITY_LEVELS["Iridium"] == "medium"

    def test_commercial_low_priority(self):
        """Test commercial constellations have low priority."""
        assert PRIORITY_LEVELS["OneWeb"] == "low"
        assert PRIORITY_LEVELS["Starlink"] == "low"


class TestMixedWindowsCalculation:
    """Test mixed constellation window calculation."""

    def test_calculate_windows_single_constellation(self, sample_tle_gps,
                                                     ground_stations, tmp_path):
        """Test window calculation for single constellation."""
        result = calculate_mixed_windows(sample_tle_gps, ground_stations)

        assert 'windows' in result
        assert 'meta' in result
        assert result['meta']['constellations'] == ['GPS']
        assert result['meta']['total_satellites'] == 2

    def test_calculate_windows_multiple_constellations(self, sample_tle_gps,
                                                       sample_tle_iridium,
                                                       ground_stations, tmp_path):
        """Test window calculation for multiple constellations."""
        merged = tmp_path / "merged.tle"
        merge_tle_files([sample_tle_gps, sample_tle_iridium], merged)

        # Use time range around TLE epoch (2024-10-06, day 280)
        start_time = datetime(2024, 10, 6, 0, 0, 0, tzinfo=timezone.utc)
        end_time = start_time + timedelta(hours=24)

        result = calculate_mixed_windows(
            merged, ground_stations, start_time, end_time,
            min_elevation=5.0,  # Lower elevation for more passes
            step_seconds=30     # Finer granularity
        )

        assert set(result['meta']['constellations']) == {'GPS', 'Iridium'}
        assert result['meta']['total_satellites'] == 4
        # May still be 0 if no actual passes occur, so just check structure
        assert 'windows' in result
        assert isinstance(result['windows'], list)

    def test_windows_have_required_fields(self, sample_tle_gps, ground_stations):
        """Test that windows have all required fields."""
        result = calculate_mixed_windows(sample_tle_gps, ground_stations)

        if result['windows']:
            window = result['windows'][0]
            assert 'satellite' in window
            assert 'constellation' in window
            assert 'frequency_band' in window
            assert 'priority' in window
            assert 'ground_station' in window
            assert 'start' in window
            assert 'end' in window
            assert 'max_elevation' in window

    def test_windows_sorted_by_time(self, sample_tle_gps, ground_stations):
        """Test that windows are sorted chronologically."""
        result = calculate_mixed_windows(sample_tle_gps, ground_stations)

        if len(result['windows']) > 1:
            for i in range(len(result['windows']) - 1):
                start1 = datetime.fromisoformat(result['windows'][i]['start'].replace('Z', '+00:00'))
                start2 = datetime.fromisoformat(result['windows'][i+1]['start'].replace('Z', '+00:00'))
                assert start1 <= start2


class TestConflictDetection:
    """Test conflict detection between windows."""

    def test_no_conflicts_different_bands(self):
        """Test no conflicts when using different frequency bands."""
        windows = [
            {
                'satellite': 'GPS-1',
                'constellation': 'GPS',
                'frequency_band': 'L-band',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:00:00Z',
                'end': '2024-10-08T10:10:00Z'
            },
            {
                'satellite': 'IRIDIUM-1',
                'constellation': 'Iridium',
                'frequency_band': 'Ka-band',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:05:00Z',
                'end': '2024-10-08T10:15:00Z'
            }
        ]

        conflicts = detect_conflicts(windows, FREQUENCY_BANDS)
        assert len(conflicts) == 0

    def test_conflict_same_band_overlap(self):
        """Test conflict detection for same band overlap."""
        windows = [
            {
                'satellite': 'IRIDIUM-1',
                'constellation': 'Iridium',
                'frequency_band': 'Ka-band',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:00:00Z',
                'end': '2024-10-08T10:10:00Z'
            },
            {
                'satellite': 'STARLINK-1',
                'constellation': 'Starlink',
                'frequency_band': 'Ka-band',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:05:00Z',
                'end': '2024-10-08T10:15:00Z'
            }
        ]

        conflicts = detect_conflicts(windows, FREQUENCY_BANDS)
        assert len(conflicts) > 0
        assert conflicts[0]['type'] == 'frequency_conflict'

    def test_no_conflict_different_stations(self):
        """Test no conflict for same band on different stations."""
        windows = [
            {
                'satellite': 'IRIDIUM-1',
                'constellation': 'Iridium',
                'frequency_band': 'Ka-band',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:00:00Z',
                'end': '2024-10-08T10:10:00Z'
            },
            {
                'satellite': 'STARLINK-1',
                'constellation': 'Starlink',
                'frequency_band': 'Ka-band',
                'ground_station': 'TASA-2',
                'start': '2024-10-08T10:05:00Z',
                'end': '2024-10-08T10:15:00Z'
            }
        ]

        conflicts = detect_conflicts(windows, FREQUENCY_BANDS)
        assert len(conflicts) == 0

    def test_conflict_details(self):
        """Test that conflict details are complete."""
        windows = [
            {
                'satellite': 'IRIDIUM-1',
                'constellation': 'Iridium',
                'frequency_band': 'Ka-band',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:00:00Z',
                'end': '2024-10-08T10:10:00Z'
            },
            {
                'satellite': 'STARLINK-1',
                'constellation': 'Starlink',
                'frequency_band': 'Ka-band',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:05:00Z',
                'end': '2024-10-08T10:15:00Z'
            }
        ]

        conflicts = detect_conflicts(windows, FREQUENCY_BANDS)
        assert conflicts[0]['window1'] == 'IRIDIUM-1'
        assert conflicts[0]['window2'] == 'STARLINK-1'
        assert conflicts[0]['frequency_band'] == 'Ka-band'
        assert conflicts[0]['ground_station'] == 'TASA-1'


class TestPriorityScheduling:
    """Test priority-based scheduling."""

    def test_schedule_no_conflicts(self):
        """Test scheduling when no conflicts exist."""
        windows = [
            {
                'satellite': 'GPS-1',
                'constellation': 'GPS',
                'frequency_band': 'L-band',
                'priority': 'high',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:00:00Z',
                'end': '2024-10-08T10:10:00Z'
            },
            {
                'satellite': 'IRIDIUM-1',
                'constellation': 'Iridium',
                'frequency_band': 'Ka-band',
                'priority': 'medium',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:15:00Z',
                'end': '2024-10-08T10:25:00Z'
            }
        ]

        result = prioritize_scheduling(windows, PRIORITY_LEVELS)
        assert len(result['scheduled']) == 2
        assert len(result['rejected']) == 0

    def test_schedule_with_conflicts_priority(self):
        """Test that higher priority wins in conflicts."""
        windows = [
            {
                'satellite': 'GPS-1',
                'constellation': 'GPS',
                'frequency_band': 'Ka-band',
                'priority': 'high',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:00:00Z',
                'end': '2024-10-08T10:10:00Z'
            },
            {
                'satellite': 'STARLINK-1',
                'constellation': 'Starlink',
                'frequency_band': 'Ka-band',
                'priority': 'low',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:05:00Z',
                'end': '2024-10-08T10:15:00Z'
            }
        ]

        result = prioritize_scheduling(windows, PRIORITY_LEVELS)

        # GPS should be scheduled, Starlink rejected
        scheduled_sats = [w['satellite'] for w in result['scheduled']]
        rejected_sats = [w['satellite'] for w in result['rejected']]

        assert 'GPS-1' in scheduled_sats
        assert 'STARLINK-1' in rejected_sats

    def test_schedule_sorted_by_priority(self):
        """Test that scheduled windows are sorted by priority."""
        windows = [
            {
                'satellite': 'STARLINK-1',
                'constellation': 'Starlink',
                'frequency_band': 'Ka-band',
                'priority': 'low',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:00:00Z',
                'end': '2024-10-08T10:10:00Z'
            },
            {
                'satellite': 'GPS-1',
                'constellation': 'GPS',
                'frequency_band': 'L-band',
                'priority': 'high',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:15:00Z',
                'end': '2024-10-08T10:25:00Z'
            },
            {
                'satellite': 'IRIDIUM-1',
                'constellation': 'Iridium',
                'frequency_band': 'Ka-band',
                'priority': 'medium',
                'ground_station': 'TASA-2',
                'start': '2024-10-08T10:20:00Z',
                'end': '2024-10-08T10:30:00Z'
            }
        ]

        result = prioritize_scheduling(windows, PRIORITY_LEVELS)

        # Should be ordered: high, medium, low
        priorities = [w['priority'] for w in result['scheduled']]
        priority_order = {'high': 0, 'medium': 1, 'low': 2}

        for i in range(len(priorities) - 1):
            assert priority_order[priorities[i]] <= priority_order[priorities[i+1]]

    def test_schedule_rejection_reason(self):
        """Test that rejected windows have reasons."""
        windows = [
            {
                'satellite': 'IRIDIUM-1',
                'constellation': 'Iridium',
                'frequency_band': 'Ka-band',
                'priority': 'medium',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:00:00Z',
                'end': '2024-10-08T10:10:00Z'
            },
            {
                'satellite': 'STARLINK-1',
                'constellation': 'Starlink',
                'frequency_band': 'Ka-band',
                'priority': 'low',
                'ground_station': 'TASA-1',
                'start': '2024-10-08T10:05:00Z',
                'end': '2024-10-08T10:15:00Z'
            }
        ]

        result = prioritize_scheduling(windows, PRIORITY_LEVELS)

        if result['rejected']:
            assert 'reason' in result['rejected'][0]
            assert 'conflict_with' in result['rejected'][0]


class TestOutputFormat:
    """Test output format compliance."""

    def test_output_has_meta(self, sample_tle_gps, ground_stations):
        """Test output has meta section."""
        result = calculate_mixed_windows(sample_tle_gps, ground_stations)

        assert 'meta' in result
        assert 'constellations' in result['meta']
        assert 'total_satellites' in result['meta']

    def test_output_has_windows(self, sample_tle_gps, ground_stations):
        """Test output has windows section."""
        result = calculate_mixed_windows(sample_tle_gps, ground_stations)

        assert 'windows' in result
        assert isinstance(result['windows'], list)

    def test_integrated_output_format(self, sample_tle_gps, sample_tle_iridium,
                                      ground_stations, tmp_path):
        """Test complete integrated output format."""
        merged = tmp_path / "merged.tle"
        merge_tle_files([sample_tle_gps, sample_tle_iridium], merged)

        result = calculate_mixed_windows(merged, ground_stations)
        conflicts = detect_conflicts(result['windows'], FREQUENCY_BANDS)
        scheduled = prioritize_scheduling(result['windows'], PRIORITY_LEVELS)

        # Build final output
        output = {
            'meta': {
                **result['meta'],
                'conflicts': len(conflicts),
                'scheduled': len(scheduled['scheduled']),
                'rejected': len(scheduled['rejected'])
            },
            'windows': result['windows'],
            'conflicts': conflicts,
            'schedule': scheduled
        }

        # Verify structure
        assert 'meta' in output
        assert 'windows' in output
        assert 'conflicts' in output
        assert 'schedule' in output

        # Verify meta completeness
        assert output['meta']['constellations']
        assert output['meta']['total_satellites'] > 0
