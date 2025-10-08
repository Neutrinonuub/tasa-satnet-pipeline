#!/usr/bin/env python3
"""Configuration constants for TASA SatNet Pipeline.

This module provides centralized configuration for all magic numbers
used throughout the pipeline, including physical constants, latency
parameters, and network configuration defaults.
"""
from __future__ import annotations


class PhysicalConstants:
    """Physical constants for satellite communications."""

    # Speed of light in km/s
    SPEED_OF_LIGHT_KM_S = 299_792.458

    # Default satellite altitude in km (LEO)
    DEFAULT_ALTITUDE_KM = 550


class LatencyConstants:
    """Latency and processing delay constants."""

    # Transparent mode processing delay (ms)
    TRANSPARENT_PROCESSING_MS = 5.0

    # Regenerative mode processing delay (ms)
    REGENERATIVE_PROCESSING_MS = 10.0

    # Queuing delay ranges (ms)
    MIN_QUEUING_DELAY_MS = 0.5  # Low traffic
    MEDIUM_QUEUING_DELAY_MS = 2.0  # Medium traffic
    MAX_QUEUING_DELAY_MS = 5.0  # High traffic

    # Traffic thresholds for queuing delay estimation (seconds)
    LOW_TRAFFIC_THRESHOLD_SEC = 60
    MEDIUM_TRAFFIC_THRESHOLD_SEC = 300


class NetworkConstants:
    """Network configuration constants."""

    # Packet size in bytes (MTU)
    PACKET_SIZE_BYTES = 1500
    PACKET_SIZE_KB = 1.5

    # Default bandwidth in Mbps
    DEFAULT_BANDWIDTH_MBPS = 100
    DEFAULT_LINK_BANDWIDTH_MBPS = 50

    # Default utilization percentage
    DEFAULT_UTILIZATION_PERCENT = 80.0

    # Buffer size in MB
    DEFAULT_BUFFER_SIZE_MB = 10


class ValidationConstants:
    """Validation and safety constants."""

    # Maximum file size in MB
    MAX_FILE_SIZE_MB = 100
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    # Simulation duration in seconds (24 hours)
    DEFAULT_SIMULATION_DURATION_SEC = 86400


class PercentileConstants:
    """Statistical percentile values."""

    P95 = 95
    P99 = 99


class ConstellationConstants:
    """Multi-constellation configuration constants."""

    # Default priority weights for scheduling
    PRIORITY_WEIGHTS = {
        'high': 100,
        'medium': 50,
        'low': 10
    }

    # Frequency band characteristics (GHz)
    FREQUENCY_BAND_RANGES = {
        'L-band': (1.0, 2.0),      # 1-2 GHz
        'S-band': (2.0, 4.0),      # 2-4 GHz
        'C-band': (4.0, 8.0),      # 4-8 GHz
        'X-band': (8.0, 12.0),     # 8-12 GHz
        'Ku-band': (12.0, 18.0),   # 12-18 GHz
        'Ka-band': (26.5, 40.0),   # 26.5-40 GHz
        'UHF': (0.3, 1.0),         # 0.3-1 GHz
    }

    # Constellation-specific processing delays (ms)
    CONSTELLATION_PROCESSING_DELAYS = {
        'GPS': 2.0,          # Navigation processing
        'Iridium': 8.0,      # Voice/data processing
        'OneWeb': 6.0,       # Broadband processing
        'Starlink': 5.0,     # Low-latency broadband
        'Globalstar': 7.0,   # Satellite phone
        'O3B': 6.5,          # MEO backhaul
        'Unknown': 10.0      # Conservative default
    }

    # Default minimum elevation angles per constellation (degrees)
    MIN_ELEVATION_ANGLES = {
        'GPS': 5.0,          # Low elevation acceptable
        'Iridium': 8.0,      # Moderate elevation
        'OneWeb': 10.0,      # Standard elevation
        'Starlink': 10.0,    # Standard elevation
        'Globalstar': 10.0,  # Standard elevation
        'O3B': 15.0,         # Higher elevation for MEO
        'Unknown': 10.0      # Default
    }


# Convenience exports for backward compatibility
SPEED_OF_LIGHT = PhysicalConstants.SPEED_OF_LIGHT_KM_S
TRANSPARENT_PROCESSING = LatencyConstants.TRANSPARENT_PROCESSING_MS
REGENERATIVE_PROCESSING = LatencyConstants.REGENERATIVE_PROCESSING_MS
DEFAULT_BANDWIDTH = NetworkConstants.DEFAULT_BANDWIDTH_MBPS
PACKET_SIZE = NetworkConstants.PACKET_SIZE_BYTES
