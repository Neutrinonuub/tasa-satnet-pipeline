#!/usr/bin/env python3
"""Tests for configuration constants."""
from __future__ import annotations
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.constants import (
    PhysicalConstants,
    LatencyConstants,
    NetworkConstants,
    ValidationConstants,
    PercentileConstants,
    SPEED_OF_LIGHT,
    TRANSPARENT_PROCESSING,
    REGENERATIVE_PROCESSING,
    DEFAULT_BANDWIDTH,
    PACKET_SIZE,
)


class TestPhysicalConstants:
    """Test physical constants."""

    def test_speed_of_light_value(self):
        """Test speed of light constant has correct value."""
        assert PhysicalConstants.SPEED_OF_LIGHT_KM_S == 299_792.458
        assert SPEED_OF_LIGHT == 299_792.458

    def test_default_altitude(self):
        """Test default altitude is reasonable for LEO."""
        assert 400 <= PhysicalConstants.DEFAULT_ALTITUDE_KM <= 2000
        assert PhysicalConstants.DEFAULT_ALTITUDE_KM == 550


class TestLatencyConstants:
    """Test latency-related constants."""

    def test_processing_delays(self):
        """Test processing delay constants."""
        assert LatencyConstants.TRANSPARENT_PROCESSING_MS == 5.0
        assert LatencyConstants.REGENERATIVE_PROCESSING_MS == 10.0
        assert TRANSPARENT_PROCESSING == 5.0
        assert REGENERATIVE_PROCESSING == 10.0

    def test_regenerative_greater_than_transparent(self):
        """Test regenerative processing takes longer than transparent."""
        assert LatencyConstants.REGENERATIVE_PROCESSING_MS > LatencyConstants.TRANSPARENT_PROCESSING_MS

    def test_queuing_delays(self):
        """Test queuing delay constants."""
        assert LatencyConstants.MIN_QUEUING_DELAY_MS == 0.5
        assert LatencyConstants.MEDIUM_QUEUING_DELAY_MS == 2.0
        assert LatencyConstants.MAX_QUEUING_DELAY_MS == 5.0

        # Test ordering
        assert LatencyConstants.MIN_QUEUING_DELAY_MS < LatencyConstants.MEDIUM_QUEUING_DELAY_MS
        assert LatencyConstants.MEDIUM_QUEUING_DELAY_MS < LatencyConstants.MAX_QUEUING_DELAY_MS

    def test_traffic_thresholds(self):
        """Test traffic threshold constants."""
        assert LatencyConstants.LOW_TRAFFIC_THRESHOLD_SEC == 60
        assert LatencyConstants.MEDIUM_TRAFFIC_THRESHOLD_SEC == 300
        assert LatencyConstants.LOW_TRAFFIC_THRESHOLD_SEC < LatencyConstants.MEDIUM_TRAFFIC_THRESHOLD_SEC


class TestNetworkConstants:
    """Test network-related constants."""

    def test_packet_size(self):
        """Test packet size constants."""
        assert NetworkConstants.PACKET_SIZE_BYTES == 1500
        assert NetworkConstants.PACKET_SIZE_KB == 1.5
        assert PACKET_SIZE == 1500
        assert NetworkConstants.PACKET_SIZE_BYTES / 1000 == NetworkConstants.PACKET_SIZE_KB

    def test_bandwidth_constants(self):
        """Test bandwidth constants."""
        assert NetworkConstants.DEFAULT_BANDWIDTH_MBPS == 100
        assert NetworkConstants.DEFAULT_LINK_BANDWIDTH_MBPS == 50
        assert DEFAULT_BANDWIDTH == 100

    def test_utilization(self):
        """Test utilization constant."""
        assert NetworkConstants.DEFAULT_UTILIZATION_PERCENT == 80.0
        assert 0 < NetworkConstants.DEFAULT_UTILIZATION_PERCENT <= 100

    def test_buffer_size(self):
        """Test buffer size constant."""
        assert NetworkConstants.DEFAULT_BUFFER_SIZE_MB == 10


class TestValidationConstants:
    """Test validation-related constants."""

    def test_file_size_limits(self):
        """Test file size limit constants."""
        assert ValidationConstants.MAX_FILE_SIZE_MB == 100
        assert ValidationConstants.MAX_FILE_SIZE_BYTES == 100 * 1024 * 1024

    def test_simulation_duration(self):
        """Test simulation duration constant."""
        assert ValidationConstants.DEFAULT_SIMULATION_DURATION_SEC == 86400
        assert ValidationConstants.DEFAULT_SIMULATION_DURATION_SEC == 24 * 60 * 60  # 24 hours


class TestPercentileConstants:
    """Test percentile constants."""

    def test_percentile_values(self):
        """Test percentile constants."""
        assert PercentileConstants.P95 == 95
        assert PercentileConstants.P99 == 99
        assert 0 < PercentileConstants.P95 <= 100
        assert 0 < PercentileConstants.P99 <= 100


class TestConstantsUsage:
    """Test that constants are used correctly in modules."""

    def test_no_magic_numbers_in_gen_scenario(self):
        """Test gen_scenario.py uses constants instead of magic numbers."""
        from scripts.gen_scenario import ScenarioGenerator

        # Test transparent mode
        gen = ScenarioGenerator(mode='transparent')
        latency = gen._compute_base_latency()
        assert latency == LatencyConstants.TRANSPARENT_PROCESSING_MS

        # Test regenerative mode
        gen = ScenarioGenerator(mode='regenerative')
        latency = gen._compute_base_latency()
        assert latency == LatencyConstants.REGENERATIVE_PROCESSING_MS

    def test_constants_used_in_metrics(self):
        """Test metrics.py uses constants correctly."""
        from scripts.metrics import MetricsCalculator

        # Create a complete valid scenario for testing constants
        from datetime import datetime, timezone
        scenario = {
            'metadata': {
                'name': 'test_scenario',
                'mode': 'transparent',
                'generated_at': datetime.now(timezone.utc).isoformat()
            },
            'topology': {
                'satellites': [
                    {'id': 'SAT-1', 'type': 'satellite', 'name': 'SAT-1', 'orbit': 'LEO', 'altitude_km': 550}
                ],
                'gateways': [
                    {'id': 'GW-1', 'type': 'gateway', 'name': 'GW-1', 'latitude': 24.0, 'longitude': 121.0, 'capacity_mbps': 100}
                ],
                'links': []
            },
            'events': [],
            'parameters': {
                'relay_mode': 'transparent',
                'data_rate_mbps': 100
            }
        }

        calc = MetricsCalculator(scenario)

        # Test propagation delay uses speed of light constant
        delay = calc._compute_propagation_delay()
        expected_delay = (PhysicalConstants.DEFAULT_ALTITUDE_KM * 2 / PhysicalConstants.SPEED_OF_LIGHT_KM_S) * 1000
        assert abs(delay - expected_delay) < 0.01

        # Test queuing delay uses threshold constants
        assert calc._estimate_queuing_delay(30) == LatencyConstants.MIN_QUEUING_DELAY_MS
        assert calc._estimate_queuing_delay(150) == LatencyConstants.MEDIUM_QUEUING_DELAY_MS
        assert calc._estimate_queuing_delay(500) == LatencyConstants.MAX_QUEUING_DELAY_MS

    def test_parameters_generation(self):
        """Test that _get_parameters uses constants."""
        from scripts.gen_scenario import ScenarioGenerator

        gen = ScenarioGenerator(mode='transparent')
        params = gen._get_parameters()

        assert params['data_rate_mbps'] == NetworkConstants.DEFAULT_LINK_BANDWIDTH_MBPS
        assert params['simulation_duration_sec'] == ValidationConstants.DEFAULT_SIMULATION_DURATION_SEC
        assert params['buffer_size_mb'] == NetworkConstants.DEFAULT_BUFFER_SIZE_MB


class TestBackwardCompatibility:
    """Test backward compatibility exports."""

    def test_convenience_exports(self):
        """Test that convenience exports work."""
        assert SPEED_OF_LIGHT == PhysicalConstants.SPEED_OF_LIGHT_KM_S
        assert TRANSPARENT_PROCESSING == LatencyConstants.TRANSPARENT_PROCESSING_MS
        assert REGENERATIVE_PROCESSING == LatencyConstants.REGENERATIVE_PROCESSING_MS
        assert DEFAULT_BANDWIDTH == NetworkConstants.DEFAULT_BANDWIDTH_MBPS
        assert PACKET_SIZE == NetworkConstants.PACKET_SIZE_BYTES


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
