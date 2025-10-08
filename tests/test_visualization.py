"""Unit tests for visualization module - TDD approach.

Coverage map generation, satellite trajectory plotting, timeline visualization,
and interactive map creation for ground station coverage.
"""
from __future__ import annotations
import pytest
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
import tempfile
import shutil

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Visualization will be implemented after tests are written (TDD)
try:
    from visualization import (
        CoverageMapGenerator,
        SatelliteTrajectoryPlotter,
        TimelineVisualizer,
        InteractiveMapCreator,
        TAIWAN_BOUNDS
    )
except ImportError:
    # Module doesn't exist yet - TDD approach
    CoverageMapGenerator = None
    SatelliteTrajectoryPlotter = None
    TimelineVisualizer = None
    InteractiveMapCreator = None
    TAIWAN_BOUNDS = None


class TestCoverageMapGeneration:
    """Test coverage map generation functionality."""

    def test_generate_coverage_map(self, taiwan_stations_data, temp_output_dir):
        """Test basic coverage map generation for ground stations."""
        if CoverageMapGenerator is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        generator = CoverageMapGenerator(taiwan_stations_data)
        output_file = temp_output_dir / "coverage_map.png"

        # Generate coverage map
        result = generator.generate_map(
            output_path=output_file,
            title="Taiwan Ground Station Coverage"
        )

        # Verify file created
        assert output_file.exists(), "Coverage map PNG not created"
        assert output_file.stat().st_size > 0, "Coverage map file is empty"

        # Verify result metadata
        assert result['stations_plotted'] == 6, "Should plot all 6 stations"
        assert result['output_path'] == str(output_file)
        assert 'bounds' in result

        # Verify image dimensions (should be reasonable size)
        from PIL import Image
        img = Image.open(output_file)
        width, height = img.size
        assert width >= 800, "Image width too small"
        assert height >= 600, "Image height too small"

    def test_coverage_map_with_range_circles(self, taiwan_stations_data, temp_output_dir):
        """Test coverage map with range circles around stations."""
        if CoverageMapGenerator is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        generator = CoverageMapGenerator(taiwan_stations_data)
        output_file = temp_output_dir / "coverage_with_ranges.png"

        result = generator.generate_map(
            output_path=output_file,
            show_range_circles=True,
            elevation_angle_deg=10  # 10-degree elevation minimum
        )

        assert output_file.exists()
        assert result['range_circles_shown'] is True

    def test_coverage_map_color_coding(self, taiwan_stations_data, temp_output_dir):
        """Test coverage map with color coding by station type."""
        if CoverageMapGenerator is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        generator = CoverageMapGenerator(taiwan_stations_data)
        output_file = temp_output_dir / "coverage_colored.png"

        result = generator.generate_map(
            output_path=output_file,
            color_by_type=True
        )

        assert output_file.exists()
        # Should have different colors for command_control, data_downlink, telemetry, backup
        assert 'color_legend' in result
        assert len(result['color_legend']) >= 3  # At least 3 station types


class TestSatelliteTrajectoryPlotting:
    """Test satellite trajectory visualization."""

    def test_plot_satellite_trajectory(self, complex_windows_data, taiwan_stations_data, temp_output_dir):
        """Test plotting satellite ground tracks."""
        if SatelliteTrajectoryPlotter is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        plotter = SatelliteTrajectoryPlotter(
            windows=complex_windows_data['windows'],
            stations=taiwan_stations_data
        )
        output_file = temp_output_dir / "trajectories.png"

        result = plotter.plot_trajectories(
            output_path=output_file,
            satellite_filter=None  # Plot all satellites
        )

        assert output_file.exists()
        assert result['satellites_plotted'] == 6  # All 6 satellites from windows
        assert 'trajectory_points' in result

    def test_plot_single_satellite_trajectory(self, complex_windows_data, taiwan_stations_data, temp_output_dir):
        """Test plotting trajectory for a single satellite."""
        if SatelliteTrajectoryPlotter is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        plotter = SatelliteTrajectoryPlotter(
            windows=complex_windows_data['windows'],
            stations=taiwan_stations_data
        )
        output_file = temp_output_dir / "trajectory_starlink.png"

        result = plotter.plot_trajectories(
            output_path=output_file,
            satellite_filter=["STARLINK-5123"]
        )

        assert output_file.exists()
        assert result['satellites_plotted'] == 1
        assert "STARLINK-5123" in result['satellite_names']

    def test_trajectory_with_time_annotations(self, complex_windows_data, taiwan_stations_data, temp_output_dir):
        """Test trajectory plot with time annotations."""
        if SatelliteTrajectoryPlotter is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        plotter = SatelliteTrajectoryPlotter(
            windows=complex_windows_data['windows'],
            stations=taiwan_stations_data
        )
        output_file = temp_output_dir / "trajectory_annotated.png"

        result = plotter.plot_trajectories(
            output_path=output_file,
            show_time_labels=True,
            time_interval_minutes=60  # Label every hour
        )

        assert output_file.exists()
        assert result['time_annotations'] > 0


class TestTimelineVisualization:
    """Test timeline/Gantt chart visualization for windows."""

    def test_timeline_visualization(self, complex_windows_data, temp_output_dir):
        """Test basic timeline visualization of contact windows."""
        if TimelineVisualizer is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        visualizer = TimelineVisualizer(complex_windows_data['windows'])
        output_file = temp_output_dir / "timeline.png"

        result = visualizer.create_timeline(
            output_path=output_file,
            group_by='satellite'
        )

        assert output_file.exists()
        assert result['total_windows'] == 35  # From complex_windows_data
        assert result['groups'] == 6  # 6 different satellites

    def test_timeline_by_gateway(self, complex_windows_data, temp_output_dir):
        """Test timeline grouped by gateway/ground station."""
        if TimelineVisualizer is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        visualizer = TimelineVisualizer(complex_windows_data['windows'])
        output_file = temp_output_dir / "timeline_by_gateway.png"

        result = visualizer.create_timeline(
            output_path=output_file,
            group_by='gateway'
        )

        assert output_file.exists()
        # Should have groups for TAIPEI, HSINCHU, KAOHSIUNG, TAICHUNG, TAINAN, HUALIEN
        assert result['groups'] >= 5

    def test_timeline_with_window_types(self, complex_windows_data, temp_output_dir):
        """Test timeline with different colors for cmd vs xband windows."""
        if TimelineVisualizer is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        visualizer = TimelineVisualizer(complex_windows_data['windows'])
        output_file = temp_output_dir / "timeline_typed.png"

        result = visualizer.create_timeline(
            output_path=output_file,
            color_by_type=True
        )

        assert output_file.exists()
        assert 'color_legend' in result
        assert 'cmd' in result['window_types']
        assert 'xband' in result['window_types']


class TestInteractiveMapCreation:
    """Test interactive map generation with folium."""

    def test_interactive_map_creation(self, taiwan_stations_data, complex_windows_data, temp_output_dir):
        """Test basic interactive HTML map creation."""
        if InteractiveMapCreator is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        creator = InteractiveMapCreator(
            stations=taiwan_stations_data,
            windows=complex_windows_data['windows']
        )
        output_file = temp_output_dir / "interactive_map.html"

        result = creator.create_map(output_path=output_file)

        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Verify HTML structure
        html_content = output_file.read_text(encoding='utf-8')
        assert 'folium' in html_content.lower() or 'leaflet' in html_content.lower()
        assert 'taiwan' in html_content.lower() or 'TAIPEI' in html_content

    def test_interactive_map_with_coverage_circles(self, taiwan_stations_data, complex_windows_data, temp_output_dir):
        """Test interactive map with coverage circles."""
        if InteractiveMapCreator is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        creator = InteractiveMapCreator(
            stations=taiwan_stations_data,
            windows=complex_windows_data['windows']
        )
        output_file = temp_output_dir / "interactive_coverage.html"

        result = creator.create_map(
            output_path=output_file,
            show_coverage=True,
            elevation_angle_deg=5
        )

        assert output_file.exists()
        assert result['coverage_circles'] == 6  # One per station

    def test_interactive_map_with_satellite_passes(self, taiwan_stations_data, complex_windows_data, temp_output_dir):
        """Test interactive map with satellite pass markers."""
        if InteractiveMapCreator is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        creator = InteractiveMapCreator(
            stations=taiwan_stations_data,
            windows=complex_windows_data['windows']
        )
        output_file = temp_output_dir / "interactive_passes.html"

        result = creator.create_map(
            output_path=output_file,
            show_satellite_passes=True
        )

        assert output_file.exists()
        assert result['satellite_markers'] > 0


class TestExportFormats:
    """Test various export formats (PNG, SVG, HTML)."""

    def test_export_formats(self, taiwan_stations_data, temp_output_dir):
        """Test exporting in multiple formats."""
        if CoverageMapGenerator is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        generator = CoverageMapGenerator(taiwan_stations_data)

        # Test PNG export
        png_file = temp_output_dir / "export_test.png"
        result_png = generator.generate_map(output_path=png_file, format='png')
        assert png_file.exists()
        assert png_file.suffix == '.png'

        # Test SVG export (vector format)
        svg_file = temp_output_dir / "export_test.svg"
        result_svg = generator.generate_map(output_path=svg_file, format='svg')
        assert svg_file.exists()
        assert svg_file.suffix == '.svg'

        # Verify SVG is text-based vector
        svg_content = svg_file.read_text(encoding='utf-8')
        assert '<svg' in svg_content.lower()

    def test_export_with_different_dpi(self, taiwan_stations_data, temp_output_dir):
        """Test PNG export with different DPI settings."""
        if CoverageMapGenerator is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        generator = CoverageMapGenerator(taiwan_stations_data)

        # Low DPI
        low_dpi_file = temp_output_dir / "low_dpi.png"
        generator.generate_map(output_path=low_dpi_file, dpi=72)

        # High DPI
        high_dpi_file = temp_output_dir / "high_dpi.png"
        generator.generate_map(output_path=high_dpi_file, dpi=300)

        # High DPI should be larger file
        assert high_dpi_file.stat().st_size > low_dpi_file.stat().st_size


class TestTaiwanMapBounds:
    """Test Taiwan geographic bounds and coordinate validation."""

    def test_taiwan_map_bounds(self):
        """Test Taiwan map bounds constants."""
        if TAIWAN_BOUNDS is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        # Taiwan bounds: approximately 21-26°N, 119-122°E
        assert TAIWAN_BOUNDS['lat_min'] >= 20.5
        assert TAIWAN_BOUNDS['lat_max'] <= 26.5
        assert TAIWAN_BOUNDS['lon_min'] >= 118.5
        assert TAIWAN_BOUNDS['lon_max'] <= 122.5

        # Verify reasonable margins
        lat_range = TAIWAN_BOUNDS['lat_max'] - TAIWAN_BOUNDS['lat_min']
        lon_range = TAIWAN_BOUNDS['lon_max'] - TAIWAN_BOUNDS['lon_min']
        assert 4 <= lat_range <= 7  # ~5-6 degrees
        assert 2 <= lon_range <= 5  # ~3-4 degrees

    def test_station_within_bounds(self, taiwan_stations_data):
        """Test all Taiwan stations are within expected bounds."""
        if TAIWAN_BOUNDS is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        for station in taiwan_stations_data['ground_stations']:
            lat = station['lat']
            lon = station['lon']

            # All stations should be within Taiwan bounds
            assert TAIWAN_BOUNDS['lat_min'] <= lat <= TAIWAN_BOUNDS['lat_max'], \
                f"Station {station['name']} latitude {lat} out of bounds"
            assert TAIWAN_BOUNDS['lon_min'] <= lon <= TAIWAN_BOUNDS['lon_max'], \
                f"Station {station['name']} longitude {lon} out of bounds"

    def test_map_centering(self, taiwan_stations_data, temp_output_dir):
        """Test map is properly centered on Taiwan."""
        if CoverageMapGenerator is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        generator = CoverageMapGenerator(taiwan_stations_data)
        output_file = temp_output_dir / "centered_map.png"

        result = generator.generate_map(output_path=output_file)

        # Verify center is approximately in the middle of Taiwan
        center_lat = result['center_lat']
        center_lon = result['center_lon']

        assert 23 <= center_lat <= 25  # Central Taiwan
        assert 120 <= center_lon <= 121.5


class TestMultiSatelliteOverlay:
    """Test visualization of multiple satellites simultaneously."""

    def test_multi_satellite_overlay(self, complex_windows_data, taiwan_stations_data, temp_output_dir):
        """Test overlaying multiple satellite trajectories."""
        if SatelliteTrajectoryPlotter is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        plotter = SatelliteTrajectoryPlotter(
            windows=complex_windows_data['windows'],
            stations=taiwan_stations_data
        )
        output_file = temp_output_dir / "multi_satellite.png"

        result = plotter.plot_trajectories(output_path=output_file)

        assert output_file.exists()
        assert result['satellites_plotted'] == 6

        # Each satellite should have different color
        assert len(result['satellite_colors']) == 6
        assert len(set(result['satellite_colors'].values())) == 6  # All unique colors

    def test_satellite_constellation_grouping(self, complex_windows_data, taiwan_stations_data, temp_output_dir):
        """Test grouping satellites by constellation."""
        if SatelliteTrajectoryPlotter is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        plotter = SatelliteTrajectoryPlotter(
            windows=complex_windows_data['windows'],
            stations=taiwan_stations_data
        )
        output_file = temp_output_dir / "constellation_groups.png"

        result = plotter.plot_trajectories(
            output_path=output_file,
            group_by_constellation=True
        )

        assert output_file.exists()
        # Should identify STARLINK, ONEWEB, IRIDIUM, GPS constellations
        assert 'constellations' in result
        constellations = result['constellations']
        assert 'STARLINK' in constellations
        assert 'ONEWEB' in constellations
        assert 'IRIDIUM' in constellations

    def test_time_lapse_visualization(self, complex_windows_data, taiwan_stations_data, temp_output_dir):
        """Test time-lapse style visualization showing satellite positions over time."""
        if SatelliteTrajectoryPlotter is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        plotter = SatelliteTrajectoryPlotter(
            windows=complex_windows_data['windows'],
            stations=taiwan_stations_data
        )
        output_file = temp_output_dir / "time_lapse.png"

        result = plotter.plot_trajectories(
            output_path=output_file,
            time_lapse=True,
            time_step_minutes=30  # Show positions every 30 minutes
        )

        assert output_file.exists()
        assert 'time_steps' in result
        assert result['time_steps'] > 0


class TestPerformanceLargeDataset:
    """Performance tests for large datasets."""

    def test_performance_large_dataset(self, temp_output_dir, benchmark):
        """Test performance with large number of windows (1000+)."""
        if TimelineVisualizer is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        # Generate large dataset (1000 windows)
        large_windows = []
        base_time = datetime(2025, 10, 8, 0, 0, 0, tzinfo=timezone.utc)
        satellites = [f"SAT-{i:03d}" for i in range(20)]  # 20 satellites
        gateways = ["TAIPEI", "HSINCHU", "KAOHSIUNG", "TAICHUNG", "TAINAN"]

        for i in range(1000):
            sat = satellites[i % len(satellites)]
            gw = gateways[i % len(gateways)]
            window_type = "xband" if i % 2 == 0 else "cmd"

            start_offset = i * 60  # 1 minute apart
            duration = 300 + (i % 600)  # 5-15 minutes

            start_time = base_time.timestamp() + start_offset
            end_time = start_time + duration

            large_windows.append({
                "type": window_type,
                "start": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat().replace('+00:00', 'Z'),
                "end": datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat().replace('+00:00', 'Z'),
                "sat": sat,
                "gw": gw,
                "source": "test"
            })

        visualizer = TimelineVisualizer(large_windows)
        output_file = temp_output_dir / "large_timeline.png"

        def create_timeline():
            return visualizer.create_timeline(output_path=output_file)

        # Benchmark should complete in reasonable time (< 10 seconds)
        result = benchmark(create_timeline)

        assert output_file.exists()
        assert result['total_windows'] == 1000

    def test_memory_efficiency_large_map(self, temp_output_dir):
        """Test memory efficiency when generating large high-res maps."""
        if CoverageMapGenerator is None:
            pytest.skip("visualization module not implemented yet (TDD)")

        # Generate large dataset of stations
        large_stations = {
            "ground_stations": [
                {
                    "name": f"STATION-{i:03d}",
                    "lat": 21 + (i % 50) * 0.1,
                    "lon": 119 + (i % 30) * 0.1,
                    "alt": 10 + i % 100,
                    "type": "telemetry"
                }
                for i in range(100)
            ]
        }

        generator = CoverageMapGenerator(large_stations)
        output_file = temp_output_dir / "large_coverage_map.png"

        # Should handle 100 stations without excessive memory
        result = generator.generate_map(
            output_path=output_file,
            dpi=150,
            show_range_circles=True
        )

        assert output_file.exists()
        assert result['stations_plotted'] == 100

        # File size should be reasonable (< 10MB for PNG)
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        assert file_size_mb < 10, f"Output file too large: {file_size_mb:.2f} MB"


# Run tests with: pytest tests/test_visualization.py -v --cov=scripts.visualization
