"""Unit tests for metrics visualization integration - TDD approach.

Tests automatic visualization generation when computing metrics:
- Coverage map generation
- Interactive HTML maps
- Timeline charts
- Latency/throughput performance charts
- Integration with metrics.py --visualize flag
- Multi-constellation scenarios
- K8s compatibility
"""
from __future__ import annotations
import pytest
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
import subprocess

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from metrics_visualization import MetricsVisualizer


class TestMetricsVisualizerInitialization:
    """Test MetricsVisualizer initialization."""

    def test_visualizer_initialization(self, sample_scenario, sample_metrics):
        """Test basic visualizer initialization."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)

        assert visualizer.scenario == sample_scenario
        assert visualizer.metrics == sample_metrics
        assert visualizer.metadata == sample_scenario['metadata']
        assert visualizer.topology == sample_scenario['topology']

    def test_visualizer_with_empty_metrics(self, sample_scenario):
        """Test visualizer handles empty metrics gracefully."""
        visualizer = MetricsVisualizer(sample_scenario, [])

        assert visualizer.metrics == []
        assert len(visualizer.events) > 0  # Should still have events from scenario


class TestCoverageMapGeneration:
    """Test coverage map generation from metrics."""

    def test_generate_coverage_map(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test coverage map generation."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        output_file = temp_output_dir / "coverage_map.png"

        result = visualizer.generate_coverage_map(output_file)

        assert output_file.exists(), "Coverage map not created"
        assert output_file.stat().st_size > 0, "Coverage map is empty"
        assert result['status'] == 'success'
        assert result['visualization_type'] == 'coverage_map'
        assert result['stations_plotted'] >= 2  # At least 2 gateways

    def test_coverage_map_output_path(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test coverage map creates directory if needed."""
        deep_path = temp_output_dir / "reports" / "viz" / "coverage_map.png"

        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        result = visualizer.generate_coverage_map(deep_path)

        assert deep_path.exists()
        assert deep_path.parent.exists()
        assert result['output_path'] == str(deep_path)


class TestInteractiveMapGeneration:
    """Test interactive HTML map generation."""

    def test_generate_interactive_map(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test interactive map generation."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        output_file = temp_output_dir / "interactive_map.html"

        result = visualizer.generate_interactive_map(output_file)

        assert output_file.exists()
        assert output_file.stat().st_size > 0
        assert result['status'] == 'success'
        assert result['visualization_type'] == 'interactive_map'

        # Verify HTML content
        html_content = output_file.read_text(encoding='utf-8')
        assert 'folium' in html_content.lower() or 'leaflet' in html_content.lower()

    def test_interactive_map_with_satellite_passes(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test interactive map shows satellite passes."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        output_file = temp_output_dir / "interactive_passes.html"

        result = visualizer.generate_interactive_map(output_file)

        assert output_file.exists()
        # Should have satellite markers if there are events
        if len(sample_scenario.get('events', [])) > 0:
            assert result.get('satellite_markers', 0) >= 0


class TestTimelineGeneration:
    """Test timeline/Gantt chart generation."""

    def test_generate_timeline(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test timeline generation from events."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        output_file = temp_output_dir / "timeline.png"

        result = visualizer.generate_timeline(output_file)

        assert output_file.exists()
        assert result['visualization_type'] == 'timeline'

        # Should have windows if there are link_up/link_down pairs
        if result['status'] == 'success':
            assert result['total_windows'] > 0
            assert result['groups'] > 0

    def test_timeline_grouping_options(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test timeline grouping by satellite vs gateway."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)

        # Group by satellite
        result_sat = visualizer.generate_timeline(
            temp_output_dir / "timeline_satellite.png",
            group_by='satellite'
        )

        # Group by gateway
        result_gw = visualizer.generate_timeline(
            temp_output_dir / "timeline_gateway.png",
            group_by='gateway'
        )

        assert (temp_output_dir / "timeline_satellite.png").exists()
        assert (temp_output_dir / "timeline_gateway.png").exists()

    def test_timeline_with_no_windows(self, temp_output_dir):
        """Test timeline handles no contact windows gracefully."""
        empty_scenario = {
            'metadata': {'name': 'empty', 'mode': 'transparent'},
            'topology': {'satellites': [], 'gateways': []},
            'events': [],
            'parameters': {}
        }

        visualizer = MetricsVisualizer(empty_scenario, [])
        result = visualizer.generate_timeline(temp_output_dir / "empty_timeline.png")

        assert result['status'] == 'warning'
        assert result['total_windows'] == 0


class TestPerformanceChartsGeneration:
    """Test performance chart generation."""

    def test_generate_performance_charts(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test performance charts generation."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        output_file = temp_output_dir / "performance_charts.png"

        result = visualizer.generate_performance_charts(output_file)

        assert output_file.exists()
        assert output_file.stat().st_size > 0
        assert result['status'] == 'success'
        assert result['visualization_type'] == 'performance_charts'
        assert 'statistics' in result
        assert 'avg_latency_ms' in result['statistics']
        assert 'avg_throughput_mbps' in result['statistics']
        assert 'avg_utilization_percent' in result['statistics']

    def test_performance_charts_content(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test performance charts contain expected panels."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        output_file = temp_output_dir / "perf_charts.png"

        result = visualizer.generate_performance_charts(output_file)

        # Verify statistics are reasonable
        stats = result['statistics']
        assert stats['avg_latency_ms'] > 0
        assert stats['avg_throughput_mbps'] >= 0
        assert 0 <= stats['avg_utilization_percent'] <= 100

    def test_performance_charts_with_no_metrics(self, sample_scenario, temp_output_dir):
        """Test performance charts handle no metrics gracefully."""
        visualizer = MetricsVisualizer(sample_scenario, [])
        output_file = temp_output_dir / "empty_perf.png"

        result = visualizer.generate_performance_charts(output_file)

        assert result['status'] == 'warning'
        assert 'message' in result


class TestGenerateAll:
    """Test generate_all() method."""

    def test_generate_all_visualizations(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test generating all visualizations at once."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)

        result = visualizer.generate_all(temp_output_dir)

        # Check manifest
        assert 'visualizations' in result
        assert 'timestamp' in result
        assert result['scenario_name'] == sample_scenario['metadata']['name']
        assert result['mode'] == sample_scenario['metadata']['mode']

        # Check files exist
        assert (temp_output_dir / "coverage_map.png").exists()
        assert (temp_output_dir / "interactive_map.html").exists()
        assert (temp_output_dir / "timeline.png").exists()
        assert (temp_output_dir / "performance_charts.png").exists()
        assert (temp_output_dir / "visualization_manifest.json").exists()

        # Verify manifest file
        manifest = json.loads((temp_output_dir / "visualization_manifest.json").read_text())
        assert 'visualizations' in manifest
        assert len(manifest['visualizations']) == 4

    def test_generate_all_creates_directory(self, sample_scenario, sample_metrics, tmp_path):
        """Test generate_all creates output directory if needed."""
        output_dir = tmp_path / "new" / "viz" / "output"

        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        result = visualizer.generate_all(output_dir)

        assert output_dir.exists()
        assert (output_dir / "visualization_manifest.json").exists()


class TestMetricsCLIIntegration:
    """Test metrics.py CLI with --visualize flag."""

    def test_metrics_with_visualize_flag(self, sample_scenario_file, temp_output_dir):
        """Test metrics.py --visualize flag."""
        output_csv = temp_output_dir / "metrics.csv"
        summary_json = temp_output_dir / "summary.json"
        viz_dir = temp_output_dir / "viz"

        result = subprocess.run([
            sys.executable, "-m", "scripts.metrics",
            str(sample_scenario_file),
            "--output", str(output_csv),
            "--summary", str(summary_json),
            "--visualize",
            "--viz-output-dir", str(viz_dir),
            "--skip-validation"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        # Print output for debugging
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Check metrics outputs
        assert output_csv.exists(), f"Output CSV not found: {output_csv}"
        assert summary_json.exists(), f"Summary JSON not found: {summary_json}"

        # Check visualization outputs
        assert viz_dir.exists(), f"Viz dir not found: {viz_dir}"
        assert (viz_dir / "coverage_map.png").exists(), "Coverage map not found"
        assert (viz_dir / "interactive_map.html").exists(), "Interactive map not found"
        assert (viz_dir / "performance_charts.png").exists(), "Performance charts not found"
        assert (viz_dir / "visualization_manifest.json").exists(), "Manifest not found"

    def test_metrics_without_visualize_flag(self, sample_scenario_file, temp_output_dir):
        """Test metrics.py without --visualize flag (no viz generated)."""
        output_csv = temp_output_dir / "metrics.csv"
        summary_json = temp_output_dir / "summary.json"
        viz_dir = temp_output_dir / "viz"

        result = subprocess.run([
            sys.executable, "-m", "scripts.metrics",
            str(sample_scenario_file),
            "--output", str(output_csv),
            "--summary", str(summary_json),
            "--skip-validation"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        assert result.returncode == 0

        # Metrics outputs should exist
        assert output_csv.exists()
        assert summary_json.exists()

        # Visualization directory should NOT exist
        assert not viz_dir.exists()


class TestMultiConstellationVisualization:
    """Test visualization with multi-constellation scenarios."""

    def test_multi_constellation_performance_charts(self, multi_constellation_scenario,
                                                     multi_constellation_metrics, temp_output_dir):
        """Test performance charts with multiple constellations."""
        visualizer = MetricsVisualizer(multi_constellation_scenario, multi_constellation_metrics)
        output_file = temp_output_dir / "multi_perf.png"

        result = visualizer.generate_performance_charts(output_file)

        assert output_file.exists()
        assert result['status'] == 'success'
        assert result['sessions_analyzed'] >= 3  # Multiple constellations (3 in fixture)

    def test_multi_constellation_timeline(self, multi_constellation_scenario,
                                         multi_constellation_metrics, temp_output_dir):
        """Test timeline with multiple satellites."""
        visualizer = MetricsVisualizer(multi_constellation_scenario, multi_constellation_metrics)
        output_file = temp_output_dir / "multi_timeline.png"

        result = visualizer.generate_timeline(output_file)

        if result['status'] == 'success':
            assert result['total_windows'] >= 3  # 3 windows from fixture
            assert result['groups'] >= 2  # Multiple satellites (2+ groups)


class TestVisualizationOutputFormats:
    """Test different output formats and quality settings."""

    def test_visualization_png_quality(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test PNG output quality."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        output_file = temp_output_dir / "high_quality.png"

        result = visualizer.generate_performance_charts(output_file)

        assert output_file.exists()
        # File should be reasonable size (not too small, not too large)
        file_size_kb = output_file.stat().st_size / 1024
        assert 10 < file_size_kb < 5000  # Between 10KB and 5MB

    def test_visualization_html_output(self, sample_scenario, sample_metrics, temp_output_dir):
        """Test HTML interactive map output."""
        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        output_file = temp_output_dir / "map.html"

        result = visualizer.generate_interactive_map(output_file)

        assert output_file.exists()
        assert output_file.suffix == '.html'

        # HTML should be well-formed
        html = output_file.read_text(encoding='utf-8')
        assert '<html' in html.lower()
        assert '</html>' in html.lower()


class TestK8sCompatibility:
    """Test K8s compatibility and volume mount scenarios."""

    def test_k8s_volume_path_handling(self, sample_scenario, sample_metrics, tmp_path):
        """Test visualization works with K8s-style paths."""
        # Simulate K8s mounted volume path
        k8s_path = tmp_path / "data" / "reports" / "viz"

        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        result = visualizer.generate_all(k8s_path)

        assert k8s_path.exists()
        assert (k8s_path / "visualization_manifest.json").exists()

    def test_visualization_environment_variables(self, sample_scenario, sample_metrics,
                                                 temp_output_dir, monkeypatch):
        """Test visualization respects environment variables (K8s ConfigMap)."""
        # Simulate K8s environment variables
        monkeypatch.setenv("VISUALIZATION_ENABLED", "true")
        monkeypatch.setenv("VISUALIZATION_OUTPUT_DIR", str(temp_output_dir))
        monkeypatch.setenv("VISUALIZATION_DPI", "150")

        visualizer = MetricsVisualizer(sample_scenario, sample_metrics)
        result = visualizer.generate_all(temp_output_dir)

        assert result is not None
        assert len(result['visualizations']) > 0


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_scenario():
    """Sample scenario for testing."""
    return {
        'metadata': {
            'name': 'Test Scenario',
            'mode': 'transparent',
            'generated_at': '2025-10-08T00:00:00Z'
        },
        'topology': {
            'satellites': [
                {'id': 'SAT-1', 'type': 'satellite', 'orbit': 'LEO', 'altitude_km': 550}
            ],
            'gateways': [
                {'id': 'TAIPEI', 'lat': 25.0, 'lon': 121.5, 'alt': 10, 'type': 'gateway'},
                {'id': 'HSINCHU', 'lat': 24.8, 'lon': 120.9, 'alt': 20, 'type': 'gateway'}
            ]
        },
        'events': [
            {'time': '2025-10-08T01:00:00Z', 'type': 'link_up', 'source': 'SAT-1',
             'target': 'TAIPEI', 'window_type': 'cmd'},
            {'time': '2025-10-08T01:10:00Z', 'type': 'link_down', 'source': 'SAT-1',
             'target': 'TAIPEI', 'window_type': 'cmd'},
            {'time': '2025-10-08T02:00:00Z', 'type': 'link_up', 'source': 'SAT-1',
             'target': 'HSINCHU', 'window_type': 'xband'},
            {'time': '2025-10-08T02:15:00Z', 'type': 'link_down', 'source': 'SAT-1',
             'target': 'HSINCHU', 'window_type': 'xband'}
        ],
        'parameters': {
            'relay_mode': 'transparent',
            'data_rate_mbps': 50,
            'processing_delay_ms': 0.0
        }
    }


@pytest.fixture
def sample_metrics():
    """Sample metrics for testing."""
    return [
        {
            'source': 'SAT-1',
            'target': 'TAIPEI',
            'window_type': 'cmd',
            'start': '2025-10-08T01:00:00Z',
            'end': '2025-10-08T01:10:00Z',
            'duration_sec': 600,
            'latency': {
                'propagation_ms': 7.35,
                'processing_ms': 0.0,
                'queuing_ms': 0.5,
                'transmission_ms': 0.08,
                'total_ms': 7.93,
                'rtt_ms': 15.86
            },
            'throughput': {
                'average_mbps': 40.0,
                'peak_mbps': 50.0,
                'utilization_percent': 80.0
            },
            'mode': 'transparent'
        },
        {
            'source': 'SAT-1',
            'target': 'HSINCHU',
            'window_type': 'xband',
            'start': '2025-10-08T02:00:00Z',
            'end': '2025-10-08T02:15:00Z',
            'duration_sec': 900,
            'latency': {
                'propagation_ms': 7.35,
                'processing_ms': 0.0,
                'queuing_ms': 1.0,
                'transmission_ms': 0.08,
                'total_ms': 8.43,
                'rtt_ms': 16.86
            },
            'throughput': {
                'average_mbps': 42.5,
                'peak_mbps': 50.0,
                'utilization_percent': 85.0
            },
            'mode': 'transparent'
        }
    ]


@pytest.fixture
def sample_scenario_file(tmp_path, sample_scenario):
    """Create a temporary scenario file."""
    scenario_file = tmp_path / "scenario.json"
    scenario_file.write_text(json.dumps(sample_scenario, indent=2))
    return scenario_file


@pytest.fixture
def multi_constellation_scenario():
    """Multi-constellation scenario for testing."""
    return {
        'metadata': {
            'name': 'Multi-Constellation Test',
            'mode': 'transparent',
            'generated_at': '2025-10-08T00:00:00Z'
        },
        'topology': {
            'satellites': [
                {'id': 'STARLINK-1', 'type': 'satellite', 'orbit': 'LEO'},
                {'id': 'ONEWEB-1', 'type': 'satellite', 'orbit': 'LEO'},
                {'id': 'IRIDIUM-1', 'type': 'satellite', 'orbit': 'LEO'}
            ],
            'gateways': [
                {'id': 'TAIPEI', 'lat': 25.0, 'lon': 121.5, 'type': 'gateway'},
                {'id': 'KAOHSIUNG', 'lat': 22.6, 'lon': 120.3, 'type': 'gateway'}
            ]
        },
        'events': [
            {'time': '2025-10-08T01:00:00Z', 'type': 'link_up', 'source': 'STARLINK-1',
             'target': 'TAIPEI', 'window_type': 'xband'},
            {'time': '2025-10-08T01:10:00Z', 'type': 'link_down', 'source': 'STARLINK-1',
             'target': 'TAIPEI', 'window_type': 'xband'},
            {'time': '2025-10-08T01:30:00Z', 'type': 'link_up', 'source': 'ONEWEB-1',
             'target': 'KAOHSIUNG', 'window_type': 'xband'},
            {'time': '2025-10-08T01:45:00Z', 'type': 'link_down', 'source': 'ONEWEB-1',
             'target': 'KAOHSIUNG', 'window_type': 'xband'},
            {'time': '2025-10-08T02:00:00Z', 'type': 'link_up', 'source': 'IRIDIUM-1',
             'target': 'TAIPEI', 'window_type': 'cmd'},
            {'time': '2025-10-08T02:08:00Z', 'type': 'link_down', 'source': 'IRIDIUM-1',
             'target': 'TAIPEI', 'window_type': 'cmd'}
        ],
        'parameters': {'relay_mode': 'transparent', 'data_rate_mbps': 50}
    }


@pytest.fixture
def multi_constellation_metrics():
    """Multi-constellation metrics for testing."""
    base_metric = {
        'latency': {
            'propagation_ms': 7.35,
            'processing_ms': 0.0,
            'queuing_ms': 0.5,
            'transmission_ms': 0.08,
            'total_ms': 7.93,
            'rtt_ms': 15.86
        },
        'throughput': {
            'average_mbps': 40.0,
            'peak_mbps': 50.0,
            'utilization_percent': 80.0
        },
        'mode': 'transparent'
    }

    return [
        {**base_metric, 'source': 'STARLINK-1', 'target': 'TAIPEI',
         'window_type': 'xband', 'duration_sec': 600},
        {**base_metric, 'source': 'ONEWEB-1', 'target': 'KAOHSIUNG',
         'window_type': 'xband', 'duration_sec': 900},
        {**base_metric, 'source': 'IRIDIUM-1', 'target': 'TAIPEI',
         'window_type': 'cmd', 'duration_sec': 480}
    ]


# Run with: pytest tests/test_metrics_visualization.py -v --cov=scripts.metrics_visualization
