#!/usr/bin/env python3
"""
Integration test for Starlink batch processor.
Tests the actual end-to-end functionality with real data.
"""
import pytest
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from scripts.starlink_batch_processor import (
    extract_starlink_subset,
    calculate_batch_windows,
    StarlinkBatchProcessor,
)


@pytest.fixture
def data_dir() -> Path:
    """Path to data directory."""
    return Path(__file__).parent.parent / "data"


@pytest.fixture
def starlink_tle(data_dir: Path) -> Path:
    """Starlink TLE file."""
    tle_path = data_dir / "starlink.tle"
    assert tle_path.exists(), f"Starlink TLE not found: {tle_path}"
    return tle_path


@pytest.fixture
def taiwan_stations(data_dir: Path) -> list:
    """Taiwan ground stations."""
    stations_path = data_dir / "taiwan_ground_stations.json"
    assert stations_path.exists(), f"Stations not found: {stations_path}"

    with open(stations_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["ground_stations"]


class TestStarlinkIntegration:
    """Integration tests for Starlink batch processing."""

    def test_extract_10_satellites(self, starlink_tle: Path):
        """Test extracting 10 Starlink satellites."""
        satellites = extract_starlink_subset(starlink_tle, count=10)

        assert len(satellites) == 10, "Should extract exactly 10 satellites"
        assert all("name" in sat for sat in satellites), "Each must have name"
        assert all("line1" in sat for sat in satellites), "Each must have line1"
        assert all("line2" in sat for sat in satellites), "Each must have line2"

        # Verify TLE format
        for sat in satellites:
            assert sat["line1"].startswith("1 "), f"Invalid line1: {sat['line1']}"
            assert sat["line2"].startswith("2 "), f"Invalid line2: {sat['line2']}"

    def test_batch_windows_10_satellites(
        self, starlink_tle: Path, taiwan_stations: list
    ):
        """Test window calculation for 10 satellites × 6 stations."""
        # Extract 10 satellites
        satellites = extract_starlink_subset(starlink_tle, count=10)

        # Calculate windows for 24 hours
        start = datetime(2025, 10, 8, 0, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(hours=24)

        windows = calculate_batch_windows(
            satellites=satellites,
            stations=taiwan_stations,
            time_range={
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            min_elevation=10.0,
            step_sec=60,
            parallel=True,
            show_progress=False
        )

        # Verify results
        assert isinstance(windows, list), "Should return list of windows"
        assert len(windows) > 0, "Should find some visibility windows"

        for window in windows:
            assert "satellite" in window, "Window must have satellite"
            assert "station" in window, "Window must have station"
            assert "start" in window, "Window must have start time"
            assert "end" in window, "Window must have end time"
            assert "duration_sec" in window, "Window must have duration"

            # Verify station is in Taiwan
            assert window["station"] in [s["name"] for s in taiwan_stations]

            # Verify times
            start_dt = datetime.fromisoformat(window["start"].replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(window["end"].replace("Z", "+00:00"))
            assert end_dt > start_dt, "End must be after start"

    def test_batch_processor_class(
        self, starlink_tle: Path, data_dir: Path, tmp_path: Path
    ):
        """Test StarlinkBatchProcessor class."""
        # Setup
        stations_file = data_dir / "taiwan_ground_stations.json"
        output_file = tmp_path / "starlink_test_windows.json"

        # Create processor (processes 5 satellites)
        processor = StarlinkBatchProcessor(
            tle_file=starlink_tle,
            stations_file=stations_file,
            satellite_count=5,
            output_file=output_file
        )

        # Verify initialization
        assert len(processor.stations) == 6, "Should load 6 Taiwan stations"
        assert processor.satellite_count == 5

        # Note: The processor.run() method requires start/end times
        # This test verifies initialization only, since run() is complex
        # and better tested via CLI/integration tests


@pytest.mark.benchmark(group="starlink")
def test_performance_10_satellites_6_stations(
    benchmark, starlink_tle: Path, taiwan_stations: list
):
    """Benchmark 10 satellites × 6 stations."""
    def run_batch():
        satellites = extract_starlink_subset(starlink_tle, count=10)
        start = datetime(2025, 10, 8, 0, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(hours=24)

        return calculate_batch_windows(
            satellites=satellites,
            stations=taiwan_stations,
            time_range={
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            min_elevation=10.0,
            step_sec=60,
            parallel=True,
            show_progress=False
        )

    result = benchmark(run_batch)
    assert len(result) > 0, "Should produce windows"
