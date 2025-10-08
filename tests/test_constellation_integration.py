#!/usr/bin/env python3
"""
Test multi-constellation integration with gen_scenario.py and metrics.py.

This module tests the complete integration flow:
1. Multi-constellation window generation
2. Scenario generation with constellation metadata
3. Metrics calculation with per-constellation tracking
4. Conflict detection and priority scheduling
"""
from __future__ import annotations
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.gen_scenario import ScenarioGenerator
from scripts.metrics import MetricsCalculator
from scripts.constellation_manager import ConstellationManager
from scripts.multi_constellation import (
    identify_constellation,
    detect_conflicts,
    prioritize_scheduling,
    FREQUENCY_BANDS,
    PRIORITY_LEVELS
)
from config.constants import ConstellationConstants


class TestMultiConstellationScenarioGeneration:
    """Test scenario generation with multiple constellations."""

    @pytest.fixture
    def mixed_constellation_windows(self):
        """Create sample windows with multiple constellations."""
        return {
            'meta': {
                'source': 'test',
                'count': 6
            },
            'windows': [
                {
                    'satellite': 'GPS-1',
                    'constellation': 'GPS',
                    'frequency_band': 'L-band',
                    'priority': 'high',
                    'ground_station': 'HSINCHU',
                    'start': '2024-10-08T10:00:00Z',
                    'end': '2024-10-08T10:10:00Z',
                    'type': 'cmd',
                    'source': 'test'
                },
                {
                    'satellite': 'IRIDIUM-1',
                    'constellation': 'Iridium',
                    'frequency_band': 'Ka-band',
                    'priority': 'medium',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:05:00Z',
                    'end': '2024-10-08T10:15:00Z',
                    'type': 'xband',
                    'source': 'test'
                },
                {
                    'satellite': 'STARLINK-1',
                    'constellation': 'Starlink',
                    'frequency_band': 'Ka-band',
                    'priority': 'low',
                    'ground_station': 'HSINCHU',
                    'start': '2024-10-08T10:20:00Z',
                    'end': '2024-10-08T10:30:00Z',
                    'type': 'xband',
                    'source': 'test'
                },
                {
                    'satellite': 'ONEWEB-1',
                    'constellation': 'OneWeb',
                    'frequency_band': 'Ku-band',
                    'priority': 'low',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:25:00Z',
                    'end': '2024-10-08T10:35:00Z',
                    'type': 'xband',
                    'source': 'test'
                },
                {
                    'satellite': 'GPS-2',
                    'constellation': 'GPS',
                    'frequency_band': 'L-band',
                    'priority': 'high',
                    'ground_station': 'KAOHSIUNG',
                    'start': '2024-10-08T10:30:00Z',
                    'end': '2024-10-08T10:40:00Z',
                    'type': 'cmd',
                    'source': 'test'
                },
                {
                    'satellite': 'IRIDIUM-2',
                    'constellation': 'Iridium',
                    'frequency_band': 'Ka-band',
                    'priority': 'medium',
                    'ground_station': 'HSINCHU',
                    'start': '2024-10-08T10:35:00Z',
                    'end': '2024-10-08T10:45:00Z',
                    'type': 'xband',
                    'source': 'test'
                }
            ]
        }

    def test_multi_constellation_scenario_generation(self, mixed_constellation_windows):
        """Test generating NS-3 scenario from multi-constellation windows."""
        generator = ScenarioGenerator(mode='transparent', enable_constellation_support=True)
        scenario = generator.generate(mixed_constellation_windows, skip_validation=True)

        # Verify metadata
        assert 'metadata' in scenario
        assert 'constellations' in scenario['metadata']
        assert set(scenario['metadata']['constellations']) == {'GPS', 'Iridium', 'Starlink', 'OneWeb'}
        assert scenario['metadata']['constellation_count'] == 4
        assert scenario['metadata']['multi_constellation'] is True

        # Verify topology
        assert 'topology' in scenario
        satellites = scenario['topology']['satellites']
        assert len(satellites) == 6

        # Check that satellites have constellation metadata
        for sat in satellites:
            assert 'constellation' in sat
            assert 'frequency_band' in sat
            assert 'priority' in sat
            assert 'processing_delay_ms' in sat

        # Verify constellation summary
        assert 'constellation_summary' in scenario['topology']
        summary = scenario['topology']['constellation_summary']
        assert summary['GPS'] == 2
        assert summary['Iridium'] == 2
        assert summary['Starlink'] == 1
        assert summary['OneWeb'] == 1

    def test_scenario_events_include_constellation_metadata(self, mixed_constellation_windows):
        """Test that events include constellation metadata."""
        generator = ScenarioGenerator(mode='transparent', enable_constellation_support=True)
        scenario = generator.generate(mixed_constellation_windows, skip_validation=True)

        events = scenario['events']
        assert len(events) > 0

        # Check first link_up event
        link_up_events = [e for e in events if e['type'] == 'link_up']
        assert len(link_up_events) == 6

        for event in link_up_events:
            assert 'constellation' in event
            assert 'frequency_band' in event
            assert 'priority' in event

    def test_constellation_specific_processing_delays(self, mixed_constellation_windows):
        """Test that constellation-specific processing delays are applied."""
        generator = ScenarioGenerator(mode='transparent', enable_constellation_support=True)
        scenario = generator.generate(mixed_constellation_windows, skip_validation=True)

        links = scenario['topology']['links']

        # Find GPS and Starlink links
        gps_links = [l for l in links if l.get('constellation') == 'GPS']
        starlink_links = [l for l in links if l.get('constellation') == 'Starlink']

        assert len(gps_links) > 0
        assert len(starlink_links) > 0

        # GPS should have lower processing delay than Starlink
        gps_delay = gps_links[0]['latency_ms']
        starlink_delay = starlink_links[0]['latency_ms']

        # Verify delays include constellation-specific components
        assert gps_delay > 0
        assert starlink_delay > 0


class TestConflictDetectionIntegration:
    """Test conflict detection in scenario generation."""

    @pytest.fixture
    def conflicting_windows(self):
        """Create windows with frequency conflicts."""
        return {
            'meta': {'source': 'test', 'count': 3},
            'windows': [
                {
                    'satellite': 'IRIDIUM-1',
                    'constellation': 'Iridium',
                    'frequency_band': 'Ka-band',
                    'priority': 'medium',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:00:00Z',
                    'end': '2024-10-08T10:10:00Z',
                    'type': 'xband',
                    'source': 'test'
                },
                {
                    'satellite': 'STARLINK-1',
                    'constellation': 'Starlink',
                    'frequency_band': 'Ka-band',
                    'priority': 'low',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:05:00Z',
                    'end': '2024-10-08T10:15:00Z',
                    'type': 'xband',
                    'source': 'test'
                },
                {
                    'satellite': 'GPS-1',
                    'constellation': 'GPS',
                    'frequency_band': 'L-band',
                    'priority': 'high',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:07:00Z',
                    'end': '2024-10-08T10:17:00Z',
                    'type': 'cmd',
                    'source': 'test'
                }
            ]
        }

    def test_detect_frequency_conflicts(self, conflicting_windows):
        """Test conflict detection for same frequency band."""
        windows = conflicting_windows['windows']
        conflicts = detect_conflicts(windows, FREQUENCY_BANDS)

        # Should detect Ka-band conflict between Iridium and Starlink
        assert len(conflicts) > 0

        ka_conflicts = [c for c in conflicts if c['frequency_band'] == 'Ka-band']
        assert len(ka_conflicts) == 1

        conflict = ka_conflicts[0]
        assert conflict['ground_station'] == 'TAIPEI'
        assert set([conflict['constellation1'], conflict['constellation2']]) == {'Iridium', 'Starlink'}

    def test_no_conflict_different_bands(self, conflicting_windows):
        """Test that different frequency bands don't conflict."""
        windows = conflicting_windows['windows']
        conflicts = detect_conflicts(windows, FREQUENCY_BANDS)

        # GPS uses L-band, shouldn't conflict with Ka-band
        gps_in_conflicts = [
            c for c in conflicts
            if 'GPS' in [c['constellation1'], c['constellation2']]
        ]
        assert len(gps_in_conflicts) == 0


class TestPriorityScheduling:
    """Test priority-based scheduling integration."""

    def test_schedule_with_conflicts_priority(self):
        """Test that higher priority wins in conflicts."""
        windows = [
            {
                'satellite': 'GPS-1',
                'constellation': 'GPS',
                'frequency_band': 'Ka-band',
                'priority': 'high',
                'ground_station': 'TAIPEI',
                'start': '2024-10-08T10:00:00Z',
                'end': '2024-10-08T10:10:00Z'
            },
            {
                'satellite': 'STARLINK-1',
                'constellation': 'Starlink',
                'frequency_band': 'Ka-band',
                'priority': 'low',
                'ground_station': 'TAIPEI',
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
        assert len(result['rejected']) > 0
        assert 'reason' in result['rejected'][0]


class TestMetricsWithConstellations:
    """Test metrics calculation with constellation metadata."""

    @pytest.fixture
    def constellation_scenario(self):
        """Create scenario with constellation metadata."""
        return {
            'metadata': {
                'mode': 'transparent',
                'constellations': ['GPS', 'Iridium']
            },
            'topology': {
                'satellites': [
                    {'id': 'GPS-1', 'constellation': 'GPS'},
                    {'id': 'IRIDIUM-1', 'constellation': 'Iridium'}
                ],
                'gateways': [{'id': 'TAIPEI'}],
                'links': []
            },
            'events': [
                {
                    'time': '2024-10-08T10:00:00Z',
                    'type': 'link_up',
                    'source': 'GPS-1',
                    'target': 'TAIPEI',
                    'constellation': 'GPS',
                    'frequency_band': 'L-band',
                    'priority': 'high',
                    'window_type': 'cmd'
                },
                {
                    'time': '2024-10-08T10:10:00Z',
                    'type': 'link_down',
                    'source': 'GPS-1',
                    'target': 'TAIPEI',
                    'constellation': 'GPS',
                    'frequency_band': 'L-band',
                    'priority': 'high',
                    'window_type': 'cmd'
                },
                {
                    'time': '2024-10-08T10:15:00Z',
                    'type': 'link_up',
                    'source': 'IRIDIUM-1',
                    'target': 'TAIPEI',
                    'constellation': 'Iridium',
                    'frequency_band': 'Ka-band',
                    'priority': 'medium',
                    'window_type': 'xband'
                },
                {
                    'time': '2024-10-08T10:25:00Z',
                    'type': 'link_down',
                    'source': 'IRIDIUM-1',
                    'target': 'TAIPEI',
                    'constellation': 'Iridium',
                    'frequency_band': 'Ka-band',
                    'priority': 'medium',
                    'window_type': 'xband'
                }
            ],
            'parameters': {
                'data_rate_mbps': 50,
                'processing_delay_ms': 5.0
            }
        }

    def test_per_constellation_metrics(self, constellation_scenario):
        """Test that per-constellation metrics are computed."""
        calculator = MetricsCalculator(
            constellation_scenario,
            skip_validation=True,
            enable_constellation_metrics=True
        )

        metrics = calculator.compute_all_metrics()
        assert len(metrics) == 2

        # Check that metrics have constellation metadata
        for metric in metrics:
            assert 'constellation' in metric
            assert 'frequency_band' in metric
            assert 'priority' in metric

        # Check constellation tracking
        assert 'GPS' in calculator.constellation_metrics
        assert 'Iridium' in calculator.constellation_metrics
        assert len(calculator.constellation_metrics['GPS']) == 1
        assert len(calculator.constellation_metrics['Iridium']) == 1

    def test_constellation_stats_in_summary(self, constellation_scenario):
        """Test that summary includes per-constellation stats."""
        calculator = MetricsCalculator(
            constellation_scenario,
            skip_validation=True,
            enable_constellation_metrics=True
        )

        calculator.compute_all_metrics()
        summary = calculator.generate_summary()

        assert 'constellation_stats' in summary
        assert 'GPS' in summary['constellation_stats']
        assert 'Iridium' in summary['constellation_stats']

        gps_stats = summary['constellation_stats']['GPS']
        assert 'sessions' in gps_stats
        assert 'latency' in gps_stats
        assert 'throughput' in gps_stats
        assert gps_stats['sessions'] == 1

    def test_constellation_specific_processing_in_metrics(self, constellation_scenario):
        """Test that constellation-specific processing delays affect metrics."""
        calculator = MetricsCalculator(
            constellation_scenario,
            skip_validation=True,
            enable_constellation_metrics=True
        )

        metrics = calculator.compute_all_metrics()

        # Find GPS and Iridium metrics
        gps_metric = next(m for m in metrics if m['constellation'] == 'GPS')
        iridium_metric = next(m for m in metrics if m['constellation'] == 'Iridium')

        # Both should have processing delays
        assert gps_metric['latency']['processing_ms'] > 0
        assert iridium_metric['latency']['processing_ms'] > 0

        # Iridium should have higher processing delay (8ms vs 2ms)
        assert iridium_metric['latency']['processing_ms'] > gps_metric['latency']['processing_ms']


class TestConstellationManager:
    """Test ConstellationManager class."""

    def test_constellation_manager_creation(self, tmp_path):
        """Test creating and using ConstellationManager."""
        manager = ConstellationManager()

        # Add constellations
        manager.add_constellation('GPS', ['GPS-1', 'GPS-2'])
        manager.add_constellation('Iridium', ['IRIDIUM-1', 'IRIDIUM-2'])

        assert len(manager.constellations) == 2
        assert 'GPS' in manager.constellations
        assert 'Iridium' in manager.constellations
        assert manager.constellations['GPS'].satellite_count == 2

    def test_load_windows_from_json(self, tmp_path):
        """Test loading windows from JSON file."""
        windows_data = {
            'meta': {'count': 2},
            'windows': [
                {
                    'satellite': 'GPS-1',
                    'constellation': 'GPS',
                    'frequency_band': 'L-band',
                    'priority': 'high',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:00:00Z',
                    'end': '2024-10-08T10:10:00Z'
                },
                {
                    'satellite': 'IRIDIUM-1',
                    'constellation': 'Iridium',
                    'frequency_band': 'Ka-band',
                    'priority': 'medium',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:15:00Z',
                    'end': '2024-10-08T10:25:00Z'
                }
            ]
        }

        windows_file = tmp_path / 'windows.json'
        windows_file.write_text(json.dumps(windows_data))

        manager = ConstellationManager()
        count = manager.load_windows_from_json(windows_file)

        assert count == 2
        assert 'GPS' in manager.constellations
        assert 'Iridium' in manager.constellations

    def test_get_constellation_stats(self, tmp_path):
        """Test constellation statistics generation."""
        windows_data = {
            'meta': {'count': 3},
            'windows': [
                {
                    'satellite': 'GPS-1',
                    'constellation': 'GPS',
                    'frequency_band': 'L-band',
                    'priority': 'high',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:00:00Z',
                    'end': '2024-10-08T10:10:00Z'
                },
                {
                    'satellite': 'GPS-2',
                    'constellation': 'GPS',
                    'frequency_band': 'L-band',
                    'priority': 'high',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:15:00Z',
                    'end': '2024-10-08T10:25:00Z'
                },
                {
                    'satellite': 'STARLINK-1',
                    'constellation': 'Starlink',
                    'frequency_band': 'Ka-band',
                    'priority': 'low',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:20:00Z',
                    'end': '2024-10-08T10:30:00Z'
                }
            ]
        }

        windows_file = tmp_path / 'windows.json'
        windows_file.write_text(json.dumps(windows_data))

        manager = ConstellationManager()
        manager.load_windows_from_json(windows_file)
        manager.get_scheduling_order()

        stats = manager.get_constellation_stats()

        assert 'GPS' in stats
        assert 'Starlink' in stats
        assert stats['GPS']['metadata']['satellite_count'] == 2
        assert stats['GPS']['total_windows'] == 2
        assert stats['Starlink']['total_windows'] == 1


class TestFrequencyBandAssignment:
    """Test frequency band assignment and tracking."""

    def test_frequency_band_assignment(self):
        """Test that constellations get correct frequency bands."""
        assert FREQUENCY_BANDS['GPS'] == 'L-band'
        assert FREQUENCY_BANDS['Iridium'] == 'Ka-band'
        assert FREQUENCY_BANDS['OneWeb'] == 'Ku-band'
        assert FREQUENCY_BANDS['Starlink'] == 'Ka-band'

    def test_frequency_band_in_scenario(self, tmp_path):
        """Test that frequency bands appear in generated scenarios."""
        windows_data = {
            'meta': {'count': 1},
            'windows': [
                {
                    'satellite': 'GPS-1',
                    'constellation': 'GPS',
                    'frequency_band': 'L-band',
                    'priority': 'high',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:00:00Z',
                    'end': '2024-10-08T10:10:00Z',
                    'type': 'cmd',
                    'source': 'test'
                }
            ]
        }

        generator = ScenarioGenerator(mode='transparent', enable_constellation_support=True)
        scenario = generator.generate(windows_data, skip_validation=True)

        # Check that satellites have frequency_band
        satellites = scenario['topology']['satellites']
        assert all('frequency_band' in sat for sat in satellites)

        # Check that GPS has L-band
        gps_sat = next(s for s in satellites if s['id'] == 'GPS-1')
        assert gps_sat['frequency_band'] == 'L-band'


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""

    def test_complete_workflow(self, tmp_path):
        """Test complete workflow from windows to metrics."""
        # Step 1: Create multi-constellation windows
        windows_data = {
            'meta': {'source': 'test', 'count': 2},
            'windows': [
                {
                    'satellite': 'GPS-1',
                    'constellation': 'GPS',
                    'frequency_band': 'L-band',
                    'priority': 'high',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:00:00Z',
                    'end': '2024-10-08T10:10:00Z',
                    'type': 'cmd',
                    'source': 'test'
                },
                {
                    'satellite': 'STARLINK-1',
                    'constellation': 'Starlink',
                    'frequency_band': 'Ka-band',
                    'priority': 'low',
                    'ground_station': 'TAIPEI',
                    'start': '2024-10-08T10:15:00Z',
                    'end': '2024-10-08T10:25:00Z',
                    'type': 'xband',
                    'source': 'test'
                }
            ]
        }

        # Step 2: Generate scenario
        generator = ScenarioGenerator(mode='transparent', enable_constellation_support=True)
        scenario = generator.generate(windows_data, skip_validation=True)

        assert 'metadata' in scenario
        assert 'constellations' in scenario['metadata']
        assert len(scenario['metadata']['constellations']) == 2

        # Step 3: Compute metrics
        calculator = MetricsCalculator(scenario, skip_validation=True, enable_constellation_metrics=True)
        metrics = calculator.compute_all_metrics()

        assert len(metrics) == 2
        assert all('constellation' in m for m in metrics)

        # Step 4: Generate summary
        summary = calculator.generate_summary()

        assert 'constellation_stats' in summary
        assert 'GPS' in summary['constellation_stats']
        assert 'Starlink' in summary['constellation_stats']

        # Step 5: Export CSV
        csv_path = tmp_path / 'metrics.csv'
        calculator.export_csv(csv_path)

        assert csv_path.exists()
        content = csv_path.read_text()
        assert 'constellation' in content
        assert 'frequency_band' in content
        assert 'priority' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
