#!/usr/bin/env python3
"""Metrics visualization module - generate charts and maps from metrics results.

This module integrates with the existing visualization module to automatically
generate comprehensive visualizations when computing metrics:
- Coverage maps (static PNG)
- Interactive maps (HTML)
- Timeline charts (PNG)
- Performance charts: latency breakdown, throughput, utilization (PNG)

Designed for K8s compatibility with configurable output directories.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import warnings

# Suppress matplotlib warnings in server environments
warnings.filterwarnings('ignore', category=UserWarning)

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Import existing visualization components
try:
    from visualization import (
        CoverageMapGenerator,
        InteractiveMapCreator,
        TimelineVisualizer,
        SatelliteTrajectoryPlotter,
        WINDOW_TYPE_COLORS,
    )
except ImportError:
    from scripts.visualization import (
        CoverageMapGenerator,
        InteractiveMapCreator,
        TimelineVisualizer,
        SatelliteTrajectoryPlotter,
        WINDOW_TYPE_COLORS,
    )


class MetricsVisualizer:
    """Orchestrate visualization generation from metrics results.

    This class integrates with existing visualization components to automatically
    generate all necessary charts and maps when metrics are computed.
    """

    def __init__(self, scenario: Dict, metrics_results: List[Dict]):
        """Initialize visualizer with scenario and metrics data.

        Args:
            scenario: NS-3 scenario data (topology, events, parameters)
            metrics_results: List of computed metrics from MetricsCalculator
        """
        self.scenario = scenario
        self.metrics = metrics_results
        self.metadata = scenario.get('metadata', {})
        self.topology = scenario.get('topology', {})
        self.events = scenario.get('events', [])

    def generate_coverage_map(self, output_path: Path) -> Dict:
        """Generate static coverage map showing ground stations.

        Args:
            output_path: Output PNG file path

        Returns:
            Dictionary with generation metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract ground station data from topology
        gateways = self.topology.get('gateways', [])

        # Convert to visualization format
        stations_data = {
            'ground_stations': [
                {
                    'name': gw.get('id', gw.get('name', 'UNKNOWN')),
                    'lat': gw.get('lat', 23.7),  # Default to Taiwan center if missing
                    'lon': gw.get('lon', 120.9),
                    'alt': gw.get('alt', 0),
                    'type': gw.get('type', 'gateway'),
                    'location': gw.get('location', gw.get('id', 'UNKNOWN'))
                }
                for gw in gateways
            ]
        }

        # Generate coverage map
        generator = CoverageMapGenerator(stations_data)
        result = generator.generate_map(
            output_path=output_path,
            title=f"Ground Station Coverage - {self.metadata.get('name', 'Scenario')}",
            show_range_circles=True,
            elevation_angle_deg=10.0,
            color_by_type=True,
            format='png',
            dpi=150
        )

        result['visualization_type'] = 'coverage_map'
        return result

    def generate_interactive_map(self, output_path: Path) -> Dict:
        """Generate interactive HTML map with stations and satellite passes.

        Args:
            output_path: Output HTML file path

        Returns:
            Dictionary with generation metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert topology to visualization format
        gateways = self.topology.get('gateways', [])
        stations_data = {
            'ground_stations': [
                {
                    'name': gw.get('id', gw.get('name', 'UNKNOWN')),
                    'lat': gw.get('lat', 23.7),
                    'lon': gw.get('lon', 120.9),
                    'alt': gw.get('alt', 0),
                    'type': gw.get('type', 'gateway'),
                    'location': gw.get('location', gw.get('id', 'UNKNOWN'))
                }
                for gw in gateways
            ]
        }

        # Convert events to contact windows
        windows = self._events_to_windows(self.events)

        # Generate interactive map
        creator = InteractiveMapCreator(stations_data, windows)
        result = creator.create_map(
            output_path=output_path,
            show_coverage=True,
            elevation_angle_deg=5.0,
            show_satellite_passes=len(windows) > 0
        )

        result['visualization_type'] = 'interactive_map'
        return result

    def generate_timeline(self, output_path: Path, group_by: str = 'satellite') -> Dict:
        """Generate timeline/Gantt chart of contact windows.

        Args:
            output_path: Output PNG file path
            group_by: Group windows by 'satellite' or 'gateway'

        Returns:
            Dictionary with generation metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert events to contact windows
        windows = self._events_to_windows(self.events)

        if not windows:
            return {
                'status': 'warning',
                'visualization_type': 'timeline',
                'total_windows': 0,
                'message': 'No contact windows to visualize'
            }

        # Generate timeline
        visualizer = TimelineVisualizer(windows)
        result = visualizer.create_timeline(
            output_path=output_path,
            group_by=group_by,
            color_by_type=True
        )

        result['visualization_type'] = 'timeline'
        return result

    def generate_performance_charts(self, output_path: Path) -> Dict:
        """Generate performance charts: latency breakdown, throughput, utilization.

        Creates a multi-panel chart showing:
        - Latency breakdown by component (propagation/processing/queuing/transmission)
        - Throughput over time
        - Link utilization

        Args:
            output_path: Output PNG file path

        Returns:
            Dictionary with generation metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.metrics:
            return {
                'status': 'warning',
                'visualization_type': 'performance_charts',
                'message': 'No metrics to visualize'
            }

        # Create figure with 3 subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))

        # Extract data
        sessions = list(range(len(self.metrics)))

        # Panel 1: Latency breakdown (stacked bar chart)
        propagation = [m['latency']['propagation_ms'] for m in self.metrics]
        processing = [m['latency']['processing_ms'] for m in self.metrics]
        queuing = [m['latency']['queuing_ms'] for m in self.metrics]
        transmission = [m['latency']['transmission_ms'] for m in self.metrics]

        ax1.bar(sessions, propagation, label='Propagation', color='#4A90E2')
        ax1.bar(sessions, processing, bottom=propagation, label='Processing', color='#50C878')

        bottom = [p + pr for p, pr in zip(propagation, processing)]
        ax1.bar(sessions, queuing, bottom=bottom, label='Queuing', color='#FFB347')

        bottom = [b + q for b, q in zip(bottom, queuing)]
        ax1.bar(sessions, transmission, bottom=bottom, label='Transmission', color='#E57373')

        ax1.set_xlabel('Session Index', fontsize=11)
        ax1.set_ylabel('Latency (ms)', fontsize=11)
        ax1.set_title('Latency Breakdown by Component', fontsize=13, fontweight='bold')
        ax1.legend(loc='upper right', framealpha=0.9)
        ax1.grid(True, alpha=0.3, axis='y')

        # Panel 2: Throughput
        throughput = [m['throughput']['average_mbps'] for m in self.metrics]
        peak_throughput = [m['throughput']['peak_mbps'] for m in self.metrics]

        ax2.plot(sessions, throughput, marker='o', linewidth=2,
                markersize=6, label='Average Throughput', color='#4A90E2')
        ax2.plot(sessions, peak_throughput, linestyle='--', linewidth=1.5,
                label='Peak Capacity', color='#999999', alpha=0.7)
        ax2.fill_between(sessions, throughput, alpha=0.3, color='#4A90E2')

        ax2.set_xlabel('Session Index', fontsize=11)
        ax2.set_ylabel('Throughput (Mbps)', fontsize=11)
        ax2.set_title('Throughput Performance', fontsize=13, fontweight='bold')
        ax2.legend(loc='upper right', framealpha=0.9)
        ax2.grid(True, alpha=0.3)

        # Panel 3: Utilization
        utilization = [m['throughput']['utilization_percent'] for m in self.metrics]
        colors = ['#50C878' if u >= 70 else '#FFB347' if u >= 40 else '#E57373'
                 for u in utilization]

        ax3.bar(sessions, utilization, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        ax3.axhline(y=70, color='green', linestyle='--', linewidth=1, alpha=0.5, label='High Utilization (70%)')
        ax3.axhline(y=40, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='Medium Utilization (40%)')

        ax3.set_xlabel('Session Index', fontsize=11)
        ax3.set_ylabel('Utilization (%)', fontsize=11)
        ax3.set_title('Link Utilization', fontsize=13, fontweight='bold')
        ax3.set_ylim(0, 105)
        ax3.legend(loc='upper right', framealpha=0.9)
        ax3.grid(True, alpha=0.3, axis='y')

        # Add overall title
        mode = self.metadata.get('mode', 'unknown')
        fig.suptitle(f"Performance Metrics - {mode.upper()} Mode",
                    fontsize=15, fontweight='bold', y=0.995)

        plt.tight_layout(rect=[0, 0, 1, 0.99])
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        # Calculate statistics
        avg_latency = np.mean([m['latency']['total_ms'] for m in self.metrics])
        avg_throughput = np.mean(throughput)
        avg_utilization = np.mean(utilization)

        return {
            'status': 'success',
            'visualization_type': 'performance_charts',
            'output_path': str(output_path),
            'sessions_analyzed': len(self.metrics),
            'statistics': {
                'avg_latency_ms': round(avg_latency, 2),
                'avg_throughput_mbps': round(avg_throughput, 2),
                'avg_utilization_percent': round(avg_utilization, 2)
            }
        }

    def generate_all(self, output_dir: Path) -> Dict:
        """Generate all visualizations and save to output directory.

        Args:
            output_dir: Base output directory for all visualizations

        Returns:
            Dictionary with all generation results
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'scenario_name': self.metadata.get('name', 'unknown'),
            'mode': self.metadata.get('mode', 'unknown'),
            'visualizations': {}
        }

        # Generate each visualization
        print("Generating visualizations...")

        # 1. Coverage map
        print("  - Coverage map...")
        try:
            coverage_result = self.generate_coverage_map(output_dir / 'coverage_map.png')
            results['visualizations']['coverage_map'] = coverage_result
            print(f"    [OK] Saved: {coverage_result['output_path']}")
        except Exception as e:
            results['visualizations']['coverage_map'] = {'status': 'error', 'error': str(e)}
            print(f"    [ERROR] {e}")

        # 2. Interactive map
        print("  - Interactive map...")
        try:
            interactive_result = self.generate_interactive_map(output_dir / 'interactive_map.html')
            results['visualizations']['interactive_map'] = interactive_result
            print(f"    [OK] Saved: {output_dir / 'interactive_map.html'}")
        except Exception as e:
            results['visualizations']['interactive_map'] = {'status': 'error', 'error': str(e)}
            print(f"    [ERROR] {e}")

        # 3. Timeline
        print("  - Timeline...")
        try:
            timeline_result = self.generate_timeline(output_dir / 'timeline.png')
            results['visualizations']['timeline'] = timeline_result
            if timeline_result.get('status') != 'warning':
                print(f"    [OK] Saved: {output_dir / 'timeline.png'}")
            else:
                print(f"    [WARNING] {timeline_result.get('message', 'No data')}")
        except Exception as e:
            results['visualizations']['timeline'] = {'status': 'error', 'error': str(e)}
            print(f"    [ERROR] {e}")

        # 4. Performance charts
        print("  - Performance charts...")
        try:
            perf_result = self.generate_performance_charts(output_dir / 'performance_charts.png')
            results['visualizations']['performance_charts'] = perf_result
            if perf_result.get('status') != 'warning':
                print(f"    [OK] Saved: {perf_result['output_path']}")
            else:
                print(f"    [WARNING] {perf_result.get('message', 'No data')}")
        except Exception as e:
            results['visualizations']['performance_charts'] = {'status': 'error', 'error': str(e)}
            print(f"    [ERROR] {e}")

        # Save results manifest
        manifest_path = output_dir / 'visualization_manifest.json'
        with manifest_path.open('w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

        print(f"\n[OK] All visualizations generated in: {output_dir}")
        print(f"[OK] Manifest saved: {manifest_path}")

        return results

    def _events_to_windows(self, events: List[Dict]) -> List[Dict]:
        """Convert scenario events to contact windows format.

        Args:
            events: List of link_up/link_down events

        Returns:
            List of contact windows with start/end times
        """
        windows = []
        active_links = {}

        for event in events:
            if event['type'] == 'link_up':
                link_key = (event['source'], event['target'])
                active_links[link_key] = {
                    'start': event['time'],
                    'sat': event['source'],
                    'gw': event['target'],
                    'type': event.get('window_type', 'unknown')
                }
            elif event['type'] == 'link_down':
                link_key = (event['source'], event['target'])
                if link_key in active_links:
                    window = active_links[link_key]
                    window['end'] = event['time']
                    windows.append(window)
                    del active_links[link_key]

        return windows


def main():
    """CLI interface for metrics visualization."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate visualizations from metrics and scenario data'
    )
    parser.add_argument('scenario', type=Path, help='Scenario JSON file')
    parser.add_argument('metrics', type=Path, help='Metrics JSON file (summary)')
    parser.add_argument('--output-dir', type=Path, default=Path('reports/viz'),
                       help='Output directory for visualizations')
    parser.add_argument('--coverage-only', action='store_true',
                       help='Generate only coverage map')
    parser.add_argument('--interactive-only', action='store_true',
                       help='Generate only interactive map')
    parser.add_argument('--timeline-only', action='store_true',
                       help='Generate only timeline')
    parser.add_argument('--performance-only', action='store_true',
                       help='Generate only performance charts')

    args = parser.parse_args()

    # Load data
    with args.scenario.open(encoding='utf-8') as f:
        scenario = json.load(f)

    # Load metrics (can be summary or detailed metrics)
    with args.metrics.open(encoding='utf-8') as f:
        metrics_data = json.load(f)

    # If metrics is a summary file, we need to compute metrics from scenario
    # For now, assume detailed metrics are provided
    if isinstance(metrics_data, dict) and 'total_sessions' in metrics_data:
        # This is a summary, we need detailed metrics
        print("Warning: Summary metrics provided, need detailed metrics for full visualization")
        metrics_list = []
    else:
        metrics_list = metrics_data if isinstance(metrics_data, list) else []

    # Create visualizer
    visualizer = MetricsVisualizer(scenario, metrics_list)

    # Generate requested visualizations
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.coverage_only:
        result = visualizer.generate_coverage_map(args.output_dir / 'coverage_map.png')
        print(json.dumps(result, indent=2))
    elif args.interactive_only:
        result = visualizer.generate_interactive_map(args.output_dir / 'interactive_map.html')
        print(json.dumps(result, indent=2))
    elif args.timeline_only:
        result = visualizer.generate_timeline(args.output_dir / 'timeline.png')
        print(json.dumps(result, indent=2))
    elif args.performance_only:
        result = visualizer.generate_performance_charts(args.output_dir / 'performance_charts.png')
        print(json.dumps(result, indent=2))
    else:
        # Generate all
        result = visualizer.generate_all(args.output_dir)
        print(json.dumps(result, indent=2))

    return 0


if __name__ == '__main__':
    sys.exit(main())
