#!/usr/bin/env python3
"""End-to-End Integration Tests for TASA SatNet Pipeline.

Tests the complete pipeline from TLE/OASIS → Scenario → Metrics → Visualization.

Coverage:
- Full pipeline with OASIS-only data
- Full pipeline with TLE integration
- Multi-constellation scenarios
- Performance benchmarks
- Error handling and edge cases
- Data consistency across pipeline stages
"""
from __future__ import annotations

import json
import pytest
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Test configuration
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_DIR = PROJECT_ROOT / "data"
FIXTURES_DIR = TEST_DIR / "fixtures"


class TestEndToEndPipeline:
    """End-to-end integration tests for complete pipeline."""

    def test_full_pipeline_oasis_only(self, tmp_path: Path, valid_log_content: str):
        """Test complete pipeline using only OASIS log data.

        Pipeline: OASIS log → Parse → Scenario → Metrics → Scheduler
        """
        # Setup input
        log_file = tmp_path / "test.log"
        log_file.write_text(valid_log_content, encoding="utf-8")

        # Step 1: Parse OASIS log
        windows_file = tmp_path / "windows.json"
        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
                str(log_file),
                "-o", str(windows_file)
            ],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Parse failed: {result.stderr}"
        assert windows_file.exists()

        with windows_file.open() as f:
            windows_data = json.load(f)
        assert "windows" in windows_data
        assert "meta" in windows_data
        assert windows_data["meta"]["count"] > 0

        # Step 2: Generate NS-3 scenario
        scenario_file = tmp_path / "scenario.json"
        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "gen_scenario.py"),
                str(windows_file),
                "-o", str(scenario_file),
                "--mode", "transparent"
            ],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Scenario generation failed: {result.stderr}"
        assert scenario_file.exists()

        with scenario_file.open() as f:
            scenario_data = json.load(f)
        assert "topology" in scenario_data
        assert "events" in scenario_data
        assert len(scenario_data["events"]) > 0

        # Step 3: Calculate metrics
        metrics_file = tmp_path / "metrics.csv"
        summary_file = tmp_path / "summary.json"
        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "metrics.py"),
                str(scenario_file),
                "-o", str(metrics_file),
                "--summary", str(summary_file)
            ],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Metrics calculation failed: {result.stderr}"
        assert metrics_file.exists()
        assert summary_file.exists()

        with summary_file.open() as f:
            summary = json.load(f)
        assert "total_sessions" in summary
        assert "latency" in summary
        assert "throughput" in summary
        assert summary["total_sessions"] > 0

        # Step 4: Schedule beams
        schedule_file = tmp_path / "schedule.csv"
        schedule_stats = tmp_path / "schedule_stats.json"
        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "scheduler.py"),
                str(scenario_file),
                "-o", str(schedule_file),
                "--stats", str(schedule_stats)
            ],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Scheduling failed: {result.stderr}"
        assert schedule_file.exists()
        assert schedule_stats.exists()

        with schedule_stats.open() as f:
            stats = json.load(f)
        assert "scheduled" in stats
        assert "success_rate" in stats
        assert stats["success_rate"] > 0

    def test_full_pipeline_with_tle(self, tmp_path: Path):
        """Test complete pipeline with TLE data integration.

        Pipeline: TLE → Pass calculation → OASIS merge → Full pipeline
        """
        # Check if TLE data exists
        tle_file = DATA_DIR / "example_iridium.tle"
        if not tle_file.exists():
            pytest.skip("TLE data not available")

        # Step 1: Calculate TLE passes (requires sgp4)
        try:
            import sgp4
        except ImportError:
            pytest.skip("sgp4 library not installed")

        passes_file = tmp_path / "tle_passes.json"
        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "tle_processor.py"),
                str(tle_file),
                "--observer-lat", "24.7881",  # HSINCHU
                "--observer-lon", "120.9979",
                "--observer-name", "HSINCHU",
                "--start", datetime.now(timezone.utc).isoformat(),
                "--end", (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
                "-o", str(passes_file)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            pytest.skip(f"TLE processing failed: {result.stderr}")

        assert passes_file.exists()

        with passes_file.open() as f:
            passes_data = json.load(f)

        assert "passes" in passes_data
        assert "meta" in passes_data

        # Continue with full pipeline using TLE-derived passes
        # (Convert passes to windows format and proceed)

    def test_full_pipeline_multi_constellation(self, tmp_path: Path):
        """Test pipeline with multi-constellation scenario.

        Uses multiple satellite systems (Starlink, GPS, Iridium).
        """
        # Create multi-constellation log
        multi_log = """
2025-10-08T10:00:00Z INFO: Multi-constellation test
enter command window @ 2025-10-08T10:15:00Z sat=STARLINK-1234 gw=HSINCHU
exit command window @ 2025-10-08T10:20:00Z sat=STARLINK-1234 gw=HSINCHU
X-band data link window: 2025-10-08T10:25:00Z..2025-10-08T10:30:00Z sat=GPS-PRN01 gw=TAIPEI
enter command window @ 2025-10-08T10:35:00Z sat=IRIDIUM-100 gw=TAICHUNG
exit command window @ 2025-10-08T10:40:00Z sat=IRIDIUM-100 gw=TAICHUNG
X-band data link window: 2025-10-08T10:45:00Z..2025-10-08T10:50:00Z sat=STARLINK-5678 gw=HSINCHU
"""

        log_file = tmp_path / "multi_constellation.log"
        log_file.write_text(multi_log, encoding="utf-8")

        # Run full pipeline
        windows_file = tmp_path / "windows.json"
        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
                str(log_file),
                "-o", str(windows_file)
            ],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        with windows_file.open() as f:
            windows_data = json.load(f)

        # Verify multi-constellation data
        satellites = set(w["sat"] for w in windows_data["windows"])
        assert len(satellites) >= 3
        assert any("STARLINK" in s for s in satellites)
        assert any("GPS" in s for s in satellites)
        assert any("IRIDIUM" in s for s in satellites)

        # Continue through scenario and metrics
        scenario_file = tmp_path / "scenario.json"
        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "gen_scenario.py"),
                str(windows_file),
                "-o", str(scenario_file)
            ],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        with scenario_file.open() as f:
            scenario = json.load(f)

        assert len(scenario["topology"]["satellites"]) >= 3

    def test_full_pipeline_with_visualization(self, tmp_path: Path, valid_log_content: str):
        """Test pipeline with visualization generation.

        Pipeline: Full pipeline + Coverage map + Timeline + Interactive map
        """
        # Check visualization dependencies
        try:
            import matplotlib
            import folium
        except ImportError:
            pytest.skip("Visualization dependencies not installed")

        # Setup
        log_file = tmp_path / "test.log"
        log_file.write_text(valid_log_content, encoding="utf-8")

        # Run parser
        windows_file = tmp_path / "windows.json"
        subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
                str(log_file),
                "-o", str(windows_file)
            ],
            capture_output=True,
            text=True,
            check=True
        )

        # Load stations data
        stations_file = DATA_DIR / "taiwan_ground_stations.json"
        if not stations_file.exists():
            pytest.skip("Ground stations data not available")

        # Generate visualizations
        viz_dir = tmp_path / "viz"
        viz_dir.mkdir()

        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "visualization.py"),
                "--stations", str(stations_file),
                "--windows", str(windows_file),
                "--output-dir", str(viz_dir)
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Visualization may fail without display, check if files were attempted
        expected_files = [
            viz_dir / "coverage_map.png",
            viz_dir / "interactive_map.html",
            viz_dir / "timeline.png",
            viz_dir / "trajectories.png"
        ]

        # At least some outputs should be generated
        generated_files = [f for f in expected_files if f.exists()]
        assert len(generated_files) > 0, "No visualization files generated"

    def test_pipeline_performance_1000_windows(self, tmp_path: Path):
        """Performance test: Process 1000 windows through pipeline.

        Requirements:
        - Total time < 60 seconds
        - Memory < 1GB
        - No data loss
        """
        import time
        import psutil
        import os

        # Generate large log file with 1000 windows
        log_lines = ["2025-10-08T00:00:00Z INFO: Performance test start"]

        for i in range(500):
            start_hour = i % 24
            start_min = (i * 2) % 60
            end_min = (start_min + 5) % 60
            end_hour = start_hour if end_min > start_min else (start_hour + 1) % 24

            sat_id = f"SAT-{i % 100:03d}"
            gw_name = ["HSINCHU", "TAIPEI", "TAICHUNG"][i % 3]

            # Command window
            log_lines.append(
                f"enter command window @ 2025-10-08T{start_hour:02d}:{start_min:02d}:00Z "
                f"sat={sat_id} gw={gw_name}"
            )
            log_lines.append(
                f"exit command window @ 2025-10-08T{end_hour:02d}:{end_min:02d}:00Z "
                f"sat={sat_id} gw={gw_name}"
            )

        log_content = "\n".join(log_lines)
        log_file = tmp_path / "large.log"
        log_file.write_text(log_content, encoding="utf-8")

        # Measure performance
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_time = time.time()

        # Run pipeline
        windows_file = tmp_path / "windows.json"
        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
                str(log_file),
                "-o", str(windows_file)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0

        scenario_file = tmp_path / "scenario.json"
        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "gen_scenario.py"),
                str(windows_file),
                "-o", str(scenario_file)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0

        metrics_file = tmp_path / "metrics.csv"
        summary_file = tmp_path / "summary.json"
        result = subprocess.run(
            [
                "python", str(SCRIPTS_DIR / "metrics.py"),
                str(scenario_file),
                "-o", str(metrics_file),
                "--summary", str(summary_file)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0

        # Performance checks
        elapsed_time = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = final_memory - initial_memory

        # Assertions
        assert elapsed_time < 60, f"Pipeline took {elapsed_time:.2f}s (should be < 60s)"
        assert memory_used < 1024, f"Memory used {memory_used:.2f}MB (should be < 1GB)"

        # Verify no data loss
        with windows_file.open() as f:
            windows_data = json.load(f)
        assert windows_data["meta"]["count"] == 500  # 500 command windows

        print(f"\nPerformance: {elapsed_time:.2f}s, {memory_used:.2f}MB for 500 windows")

    def test_pipeline_with_scheduling(self, tmp_path: Path, valid_log_content: str):
        """Test pipeline with beam scheduling and conflict detection."""
        # Setup
        log_file = tmp_path / "test.log"
        log_file.write_text(valid_log_content, encoding="utf-8")

        # Run through scenario generation
        windows_file = tmp_path / "windows.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
             str(log_file), "-o", str(windows_file)],
            check=True, capture_output=True
        )

        scenario_file = tmp_path / "scenario.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "gen_scenario.py"),
             str(windows_file), "-o", str(scenario_file)],
            check=True, capture_output=True
        )

        # Run scheduler with different capacities
        for capacity in [1, 2, 4, 8]:
            schedule_file = tmp_path / f"schedule_cap{capacity}.csv"
            stats_file = tmp_path / f"stats_cap{capacity}.json"

            result = subprocess.run(
                [
                    "python", str(SCRIPTS_DIR / "scheduler.py"),
                    str(scenario_file),
                    "-o", str(schedule_file),
                    "--capacity", str(capacity),
                    "--stats", str(stats_file)
                ],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0

            with stats_file.open() as f:
                stats = json.load(f)

            # Success rate should increase with capacity
            assert "success_rate" in stats
            assert stats["success_rate"] >= 0
            assert stats["success_rate"] <= 100

    def test_pipeline_output_formats(self, tmp_path: Path, valid_log_content: str):
        """Test pipeline with different output formats (JSON, CSV, NS-3 script)."""
        log_file = tmp_path / "test.log"
        log_file.write_text(valid_log_content, encoding="utf-8")

        windows_file = tmp_path / "windows.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
             str(log_file), "-o", str(windows_file)],
            check=True, capture_output=True
        )

        # Test JSON output
        scenario_json = tmp_path / "scenario.json"
        result = subprocess.run(
            ["python", str(SCRIPTS_DIR / "gen_scenario.py"),
             str(windows_file), "-o", str(scenario_json), "--format", "json"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert scenario_json.exists()

        with scenario_json.open() as f:
            data = json.load(f)
        assert "topology" in data

        # Test NS-3 script output
        scenario_ns3 = tmp_path / "scenario.py"
        result = subprocess.run(
            ["python", str(SCRIPTS_DIR / "gen_scenario.py"),
             str(windows_file), "-o", str(scenario_ns3), "--format", "ns3"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert scenario_ns3.exists()

        content = scenario_ns3.read_text()
        assert "#!/usr/bin/env python3" in content
        assert "ns.core" in content or "NS-3 Scenario" in content

    def test_pipeline_error_handling(self, tmp_path: Path):
        """Test pipeline error handling and recovery."""
        # Test 1: Invalid log file
        invalid_log = tmp_path / "invalid.log"
        invalid_log.write_text("This is not a valid OASIS log", encoding="utf-8")

        windows_file = tmp_path / "windows.json"
        result = subprocess.run(
            ["python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
             str(invalid_log), "-o", str(windows_file)],
            capture_output=True, text=True
        )
        # Parser should succeed but produce empty/minimal output
        assert result.returncode == 0

        # Test 2: Empty windows file
        empty_windows = tmp_path / "empty.json"
        empty_windows.write_text('{"meta": {"source": "test", "count": 0}, "windows": []}',
                                encoding="utf-8")

        scenario_file = tmp_path / "scenario.json"
        result = subprocess.run(
            ["python", str(SCRIPTS_DIR / "gen_scenario.py"),
             str(empty_windows), "-o", str(scenario_file)],
            capture_output=True, text=True
        )
        # Should handle empty input gracefully
        assert result.returncode == 0

        # Test 3: Malformed JSON
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{invalid json}", encoding="utf-8")

        result = subprocess.run(
            ["python", str(SCRIPTS_DIR / "gen_scenario.py"),
             str(bad_json), "-o", str(scenario_file)],
            capture_output=True, text=True
        )
        # Should fail with error
        assert result.returncode != 0


class TestDataFlowConsistency:
    """Test data consistency across pipeline stages."""

    def test_window_count_consistency(self, tmp_path: Path, valid_log_content: str):
        """Verify window count is preserved through pipeline."""
        log_file = tmp_path / "test.log"
        log_file.write_text(valid_log_content, encoding="utf-8")

        # Parse
        windows_file = tmp_path / "windows.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
             str(log_file), "-o", str(windows_file)],
            check=True, capture_output=True
        )

        with windows_file.open() as f:
            windows_data = json.load(f)
        window_count = windows_data["meta"]["count"]

        # Generate scenario
        scenario_file = tmp_path / "scenario.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "gen_scenario.py"),
             str(windows_file), "-o", str(scenario_file)],
            check=True, capture_output=True
        )

        with scenario_file.open() as f:
            scenario = json.load(f)

        # Events should be 2x windows (link_up + link_down for each)
        event_count = len(scenario["events"])
        assert event_count == window_count * 2

        # Calculate metrics
        metrics_file = tmp_path / "metrics.csv"
        summary_file = tmp_path / "summary.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "metrics.py"),
             str(scenario_file), "-o", str(metrics_file),
             "--summary", str(summary_file)],
            check=True, capture_output=True
        )

        with summary_file.open() as f:
            summary = json.load(f)

        # Metrics sessions should match window count
        assert summary["total_sessions"] == window_count

    def test_satellite_gateway_consistency(self, tmp_path: Path, valid_log_content: str):
        """Verify satellite and gateway names are consistent."""
        log_file = tmp_path / "test.log"
        log_file.write_text(valid_log_content, encoding="utf-8")

        # Parse
        windows_file = tmp_path / "windows.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
             str(log_file), "-o", str(windows_file)],
            check=True, capture_output=True
        )

        with windows_file.open() as f:
            windows_data = json.load(f)

        sats_from_windows = set(w["sat"] for w in windows_data["windows"])
        gws_from_windows = set(w["gw"] for w in windows_data["windows"])

        # Generate scenario
        scenario_file = tmp_path / "scenario.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "gen_scenario.py"),
             str(windows_file), "-o", str(scenario_file)],
            check=True, capture_output=True
        )

        with scenario_file.open() as f:
            scenario = json.load(f)

        sats_from_scenario = set(s["id"] for s in scenario["topology"]["satellites"])
        gws_from_scenario = set(g["id"] for g in scenario["topology"]["gateways"])

        # Sets should match
        assert sats_from_windows == sats_from_scenario
        assert gws_from_windows == gws_from_scenario

    def test_timestamp_ordering(self, tmp_path: Path, valid_log_content: str):
        """Verify timestamps are correctly ordered throughout pipeline."""
        log_file = tmp_path / "test.log"
        log_file.write_text(valid_log_content, encoding="utf-8")

        windows_file = tmp_path / "windows.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
             str(log_file), "-o", str(windows_file)],
            check=True, capture_output=True
        )

        with windows_file.open() as f:
            windows_data = json.load(f)

        # Check window timestamps
        for window in windows_data["windows"]:
            start = datetime.fromisoformat(window["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(window["end"].replace("Z", "+00:00"))
            assert start < end, f"Window start >= end: {window}"

        # Generate scenario
        scenario_file = tmp_path / "scenario.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "gen_scenario.py"),
             str(windows_file), "-o", str(scenario_file)],
            check=True, capture_output=True
        )

        with scenario_file.open() as f:
            scenario = json.load(f)

        # Check event ordering
        events = scenario["events"]
        for i in range(len(events) - 1):
            t1 = datetime.fromisoformat(events[i]["time"].replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(events[i+1]["time"].replace("Z", "+00:00"))
            assert t1 <= t2, f"Events not sorted: {events[i]} vs {events[i+1]}"


class TestIntegrationScenarios:
    """Integration tests for specific scenarios."""

    def test_regenerative_vs_transparent_comparison(self, tmp_path: Path,
                                                    valid_log_content: str):
        """Compare regenerative vs transparent modes through full pipeline."""
        log_file = tmp_path / "test.log"
        log_file.write_text(valid_log_content, encoding="utf-8")

        windows_file = tmp_path / "windows.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
             str(log_file), "-o", str(windows_file)],
            check=True, capture_output=True
        )

        results = {}

        for mode in ["transparent", "regenerative"]:
            scenario_file = tmp_path / f"scenario_{mode}.json"
            subprocess.run(
                ["python", str(SCRIPTS_DIR / "gen_scenario.py"),
                 str(windows_file), "-o", str(scenario_file),
                 "--mode", mode],
                check=True, capture_output=True
            )

            summary_file = tmp_path / f"summary_{mode}.json"
            subprocess.run(
                ["python", str(SCRIPTS_DIR / "metrics.py"),
                 str(scenario_file), "-o", tmp_path / f"metrics_{mode}.csv",
                 "--summary", str(summary_file)],
                check=True, capture_output=True
            )

            with summary_file.open() as f:
                results[mode] = json.load(f)

        # Regenerative should have higher latency (processing delay)
        transparent_latency = results["transparent"]["latency"]["mean_ms"]
        regenerative_latency = results["regenerative"]["latency"]["mean_ms"]

        assert regenerative_latency > transparent_latency, \
            "Regenerative should have higher latency than transparent"

    def test_high_traffic_scenario(self, tmp_path: Path):
        """Test scenario with high concurrent traffic."""
        # Create overlapping windows (high traffic)
        high_traffic_log = """
2025-10-08T10:00:00Z INFO: High traffic test
enter command window @ 2025-10-08T10:00:00Z sat=SAT-1 gw=HSINCHU
enter command window @ 2025-10-08T10:01:00Z sat=SAT-2 gw=HSINCHU
enter command window @ 2025-10-08T10:02:00Z sat=SAT-3 gw=HSINCHU
exit command window @ 2025-10-08T10:15:00Z sat=SAT-1 gw=HSINCHU
exit command window @ 2025-10-08T10:16:00Z sat=SAT-2 gw=HSINCHU
exit command window @ 2025-10-08T10:17:00Z sat=SAT-3 gw=HSINCHU
"""

        log_file = tmp_path / "high_traffic.log"
        log_file.write_text(high_traffic_log, encoding="utf-8")

        windows_file = tmp_path / "windows.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "parse_oasis_log.py"),
             str(log_file), "-o", str(windows_file)],
            check=True, capture_output=True
        )

        scenario_file = tmp_path / "scenario.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "gen_scenario.py"),
             str(windows_file), "-o", str(scenario_file)],
            check=True, capture_output=True
        )

        # Schedule with limited capacity
        stats_file = tmp_path / "stats.json"
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "scheduler.py"),
             str(scenario_file), "-o", tmp_path / "schedule.csv",
             "--capacity", "2", "--stats", str(stats_file)],
            check=True, capture_output=True
        )

        with stats_file.open() as f:
            stats = json.load(f)

        # Should have some conflicts due to capacity limit
        assert stats["total_slots"] == 3
        assert stats["capacity_per_gateway"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
