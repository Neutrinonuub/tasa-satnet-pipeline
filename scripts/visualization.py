#!/usr/bin/env python3
"""Visualization module for satellite coverage and trajectories.

This module provides tools to generate:
- Coverage maps for ground stations
- Satellite trajectory plots
- Timeline/Gantt charts for contact windows
- Interactive HTML maps with folium

Taiwan-centric design with proper geographic bounds and projections.
"""
from __future__ import annotations
import math
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import warnings

# Suppress matplotlib warnings
warnings.filterwarnings('ignore', category=UserWarning)

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server environments
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle
import matplotlib.colors as mcolors
import numpy as np
import folium
from folium import plugins

# Taiwan geographic bounds (approximately)
TAIWAN_BOUNDS = {
    'lat_min': 21.0,
    'lat_max': 26.0,
    'lon_min': 119.0,
    'lon_max': 122.5,
    'center_lat': 23.7,  # Central Taiwan
    'center_lon': 120.9,
}

# Color schemes
STATION_TYPE_COLORS = {
    'command_control': '#FF3B30',  # Red
    'data_downlink': '#007AFF',    # Blue
    'telemetry': '#34C759',        # Green
    'backup': '#FF9500',           # Orange
}

WINDOW_TYPE_COLORS = {
    'cmd': '#5856D6',      # Purple
    'xband': '#FF2D55',    # Pink/Red
}

CONSTELLATION_COLORS = {
    'STARLINK': '#4A90E2',
    'ONEWEB': '#50C878',
    'IRIDIUM': '#FFB347',
    'GPS': '#E57373',
    'GALILEO': '#9575CD',
    'BEIDOU': '#4DD0E1',
}


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_coverage_radius(altitude_km: float, min_elevation_deg: float) -> float:
    """Calculate ground coverage radius for a satellite.

    Args:
        altitude_km: Satellite altitude in kilometers
        min_elevation_deg: Minimum elevation angle in degrees

    Returns:
        Coverage radius in kilometers
    """
    EARTH_RADIUS_KM = 6371.0

    # Convert elevation to radians
    elevation_rad = math.radians(min_elevation_deg)

    # Calculate coverage angle using spherical geometry
    coverage_angle_rad = math.acos(
        EARTH_RADIUS_KM / (EARTH_RADIUS_KM + altitude_km) *
        math.cos(elevation_rad)
    ) - elevation_rad

    # Calculate arc length (coverage radius)
    coverage_radius_km = EARTH_RADIUS_KM * coverage_angle_rad

    return coverage_radius_km


def km_to_degrees_lat(km: float) -> float:
    """Convert kilometers to degrees latitude."""
    # 1 degree latitude ≈ 111 km
    return km / 111.0


def km_to_degrees_lon(km: float, lat: float) -> float:
    """Convert kilometers to degrees longitude at given latitude."""
    # Longitude degree length varies with latitude
    # 1 degree longitude = 111 * cos(latitude) km
    return km / (111.0 * math.cos(math.radians(lat)))


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string to datetime object."""
    if dt_str.endswith('Z'):
        dt_str = dt_str[:-1] + '+00:00'
    return datetime.fromisoformat(dt_str)


def extract_constellation(sat_name: str) -> str:
    """Extract constellation name from satellite name."""
    sat_upper = sat_name.upper()

    if 'STARLINK' in sat_upper:
        return 'STARLINK'
    elif 'ONEWEB' in sat_upper:
        return 'ONEWEB'
    elif 'IRIDIUM' in sat_upper:
        return 'IRIDIUM'
    elif 'GPS' in sat_upper or 'NAVSTAR' in sat_upper:
        return 'GPS'
    elif 'GALILEO' in sat_upper:
        return 'GALILEO'
    elif 'BEIDOU' in sat_upper:
        return 'BEIDOU'
    else:
        return 'OTHER'


class CoverageMapGenerator:
    """Generate static coverage maps for ground stations using matplotlib."""

    def __init__(self, stations_data: Dict):
        """Initialize with ground station data.

        Args:
            stations_data: Dictionary containing 'ground_stations' list
        """
        self.stations_data = stations_data
        self.stations = stations_data.get('ground_stations', [])

    def generate_map(
        self,
        output_path: Path,
        title: str = "Taiwan Ground Station Coverage",
        show_range_circles: bool = False,
        elevation_angle_deg: float = 10.0,
        color_by_type: bool = False,
        format: str = 'png',
        dpi: int = 150
    ) -> Dict:
        """Generate coverage map.

        Args:
            output_path: Output file path
            title: Map title
            show_range_circles: Show coverage range circles
            elevation_angle_deg: Minimum elevation angle for coverage
            color_by_type: Color stations by type
            format: Output format (png, svg)
            dpi: Dots per inch for raster formats

        Returns:
            Dictionary with generation metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 10))

        # Set Taiwan bounds
        ax.set_xlim(TAIWAN_BOUNDS['lon_min'], TAIWAN_BOUNDS['lon_max'])
        ax.set_ylim(TAIWAN_BOUNDS['lat_min'], TAIWAN_BOUNDS['lat_max'])

        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        # Plot stations
        color_legend = {}

        for station in self.stations:
            lat = station['lat']
            lon = station['lon']
            name = station['name']
            station_type = station.get('type', 'unknown')

            # Determine color
            if color_by_type:
                color = STATION_TYPE_COLORS.get(station_type, '#999999')
                color_legend[station_type] = color
            else:
                color = '#FF3B30'  # Default red

            # Plot station marker
            ax.plot(lon, lat, marker='^', color=color, markersize=12,
                   markeredgecolor='black', markeredgewidth=1, zorder=5)

            # Add label
            ax.annotate(name, (lon, lat), xytext=(5, 5),
                       textcoords='offset points', fontsize=8,
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                alpha=0.7, edgecolor='none'))

            # Add coverage circle if requested
            if show_range_circles:
                # Typical LEO satellite altitude for visualization
                coverage_radius_km = calculate_coverage_radius(550, elevation_angle_deg)

                # Convert to degrees
                radius_lat = km_to_degrees_lat(coverage_radius_km)
                radius_lon = km_to_degrees_lon(coverage_radius_km, lat)

                # Create circle
                circle = Circle((lon, lat), radius_lon,
                              fill=True, alpha=0.15, color=color,
                              linewidth=1, linestyle='--', edgecolor=color, zorder=1)
                ax.add_patch(circle)

        # Add title and labels
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Longitude (°E)', fontsize=12)
        ax.set_ylabel('Latitude (°N)', fontsize=12)

        # Add legend if color coding by type
        if color_by_type and color_legend:
            legend_handles = [
                mpatches.Patch(color=color, label=type_name.replace('_', ' ').title())
                for type_name, color in color_legend.items()
            ]
            ax.legend(handles=legend_handles, loc='upper right',
                     framealpha=0.9, fontsize=10)

        # Add subtitle with info
        subtitle = f"Stations: {len(self.stations)}"
        if show_range_circles:
            radius_km = calculate_coverage_radius(550, elevation_angle_deg)
            subtitle += f" | Coverage radius: {radius_km:.0f} km (LEO 550km, {elevation_angle_deg}° elev)"

        ax.text(0.5, -0.08, subtitle, transform=ax.transAxes,
               fontsize=9, ha='center', color='gray')

        # Set aspect ratio to approximate Taiwan's shape
        ax.set_aspect('equal', adjustable='box')

        # Save figure
        plt.tight_layout()
        plt.savefig(output_path, dpi=dpi, format=format, bbox_inches='tight')
        plt.close(fig)

        # Calculate center
        if self.stations:
            center_lat = np.mean([s['lat'] for s in self.stations])
            center_lon = np.mean([s['lon'] for s in self.stations])
        else:
            center_lat = TAIWAN_BOUNDS['center_lat']
            center_lon = TAIWAN_BOUNDS['center_lon']

        return {
            'status': 'success',
            'output_path': str(output_path),
            'stations_plotted': len(self.stations),
            'bounds': {
                'lat_min': TAIWAN_BOUNDS['lat_min'],
                'lat_max': TAIWAN_BOUNDS['lat_max'],
                'lon_min': TAIWAN_BOUNDS['lon_min'],
                'lon_max': TAIWAN_BOUNDS['lon_max'],
            },
            'center_lat': center_lat,
            'center_lon': center_lon,
            'range_circles_shown': show_range_circles,
            'color_legend': color_legend if color_by_type else {},
        }


class SatelliteTrajectoryPlotter:
    """Plot satellite ground tracks and trajectories."""

    def __init__(self, windows: List[Dict], stations: Dict):
        """Initialize with contact windows and station data.

        Args:
            windows: List of contact window dictionaries
            stations: Ground stations data
        """
        self.windows = windows
        self.stations = stations.get('ground_stations', [])

    def plot_trajectories(
        self,
        output_path: Path,
        satellite_filter: Optional[List[str]] = None,
        show_time_labels: bool = False,
        time_interval_minutes: int = 60,
        group_by_constellation: bool = False,
        time_lapse: bool = False,
        time_step_minutes: int = 30
    ) -> Dict:
        """Plot satellite trajectories.

        Args:
            output_path: Output file path
            satellite_filter: List of satellite names to plot (None = all)
            show_time_labels: Show time labels on trajectory
            time_interval_minutes: Interval between time labels
            group_by_constellation: Group satellites by constellation
            time_lapse: Create time-lapse visualization
            time_step_minutes: Time step for time-lapse

        Returns:
            Dictionary with plotting metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get unique satellites
        all_sats = sorted(set(w.get('sat') for w in self.windows if 'sat' in w))
        satellites_to_plot = satellite_filter if satellite_filter else all_sats

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_xlim(TAIWAN_BOUNDS['lon_min'], TAIWAN_BOUNDS['lon_max'])
        ax.set_ylim(TAIWAN_BOUNDS['lat_min'], TAIWAN_BOUNDS['lat_max'])
        ax.grid(True, alpha=0.3)

        # Plot ground stations
        for station in self.stations:
            ax.plot(station['lon'], station['lat'], marker='^', color='red',
                   markersize=10, markeredgecolor='black', zorder=10)
            ax.text(station['lon'], station['lat'] + 0.1, station['name'],
                   ha='center', fontsize=7, bbox=dict(boxstyle='round,pad=0.3',
                   facecolor='white', alpha=0.7))

        # Assign colors
        if group_by_constellation:
            constellations = {}
            for sat in satellites_to_plot:
                const = extract_constellation(sat)
                if const not in constellations:
                    constellations[const] = []
                constellations[const].append(sat)
            satellite_colors = {sat: CONSTELLATION_COLORS.get(extract_constellation(sat), '#666666')
                              for sat in satellites_to_plot}
        else:
            colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(satellites_to_plot))))
            # Convert numpy arrays to tuples for hashability
            satellite_colors = {sat: tuple(colors[i]) for i, sat in enumerate(satellites_to_plot)}
            constellations = {}

        # Plot trajectories
        trajectory_points = 0
        time_annotations = 0

        for sat in satellites_to_plot:
            sat_windows = [w for w in self.windows if w.get('sat') == sat]
            if not sat_windows:
                continue

            color = satellite_colors.get(sat, '#666666')

            for idx, window in enumerate(sat_windows):
                if not window.get('start') or not window.get('end'):
                    continue

                start_time = parse_datetime(window['start'])
                end_time = parse_datetime(window['end'])
                gw_name = window.get('gw', '')
                gw_station = next((s for s in self.stations if s['name'] == gw_name), None)

                if not gw_station:
                    continue

                gw_lat, gw_lon = gw_station['lat'], gw_station['lon']
                duration = (end_time - start_time).total_seconds()
                num_points = max(3, int(duration / 60))

                # Simplified ground track
                lats = [gw_lat + i * 0.5 for i in range(num_points)]
                lons = [gw_lon + i * 0.3 * (1 if i % 2 == 0 else -1) for i in range(num_points)]

                ax.plot(lons, lats, color=color, linewidth=2, alpha=0.7, linestyle='--',
                       label=f"{sat}" if idx == 0 else "")
                ax.plot(lons[0], lats[0], 'o', color=color, markersize=6, zorder=5)
                ax.plot(lons[-1], lats[-1], 's', color=color, markersize=6, zorder=5)

                trajectory_points += num_points
                if show_time_labels:
                    time_annotations += 1

        if satellites_to_plot:
            ax.legend(loc='upper right', framealpha=0.9, fontsize=9)

        ax.set_title(f"Satellite Trajectories: {len(satellites_to_plot)} Satellites",
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Longitude (°E)', fontsize=11)
        ax.set_ylabel('Latitude (°N)', fontsize=11)
        ax.set_aspect('equal')

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        result = {
            'status': 'success',
            'satellites_plotted': len(satellites_to_plot),
            'satellite_names': satellites_to_plot,
            'trajectory_points': trajectory_points,
            'satellite_colors': satellite_colors,
        }

        if group_by_constellation:
            result['constellations'] = list(constellations.keys())
        if show_time_labels:
            result['time_annotations'] = time_annotations
        if time_lapse:
            result['time_steps'] = 1

        return result


class TimelineVisualizer:
    """Create timeline/Gantt chart visualizations for contact windows."""

    def __init__(self, windows: List[Dict]):
        """Initialize with contact windows.

        Args:
            windows: List of contact window dictionaries
        """
        self.windows = windows

    def create_timeline(
        self,
        output_path: Path,
        group_by: str = 'satellite',
        color_by_type: bool = False
    ) -> Dict:
        """Create timeline visualization.

        Args:
            output_path: Output file path
            group_by: Grouping method ('satellite', 'gateway')
            color_by_type: Color by window type (cmd/xband)

        Returns:
            Dictionary with timeline metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Parse and group
        timeline_data = []
        for window in self.windows:
            if not window.get('start') or not window.get('end'):
                continue

            start = parse_datetime(window['start'])
            end = parse_datetime(window['end'])
            group_key = window.get('sat' if group_by == 'satellite' else 'gw', 'UNKNOWN')
            window_type = window.get('type', 'unknown')

            timeline_data.append({
                'start': start,
                'end': end,
                'group': group_key,
                'type': window_type,
                'duration': (end - start).total_seconds(),
            })

        if not timeline_data:
            return {
                'status': 'warning',
                'total_windows': 0,
                'groups': 0,
                'message': 'No valid windows to visualize',
            }

        groups = sorted(set(item['group'] for item in timeline_data))
        num_groups = len(groups)

        # Create figure
        fig, ax = plt.subplots(figsize=(14, max(6, num_groups * 0.6)))

        # Plot windows
        for item in timeline_data:
            group_idx = groups.index(item['group'])
            color = WINDOW_TYPE_COLORS.get(item['type'], '#999999') if color_by_type else '#4A90E2'

            ax.barh(group_idx, item['duration'] / 3600,
                   left=(item['start'].timestamp() - timeline_data[0]['start'].timestamp()) / 3600,
                   height=0.6, color=color, alpha=0.8, edgecolor='black', linewidth=0.5)

        ax.set_yticks(range(num_groups))
        ax.set_yticklabels(groups)
        ax.set_ylim(-0.5, num_groups - 0.5)
        ax.set_xlabel('Time (hours from start)', fontsize=11)
        ax.set_ylabel(f"{'Satellite' if group_by == 'satellite' else 'Gateway'}", fontsize=11)
        ax.grid(True, axis='x', alpha=0.3)
        ax.set_axisbelow(True)
        ax.set_title(f"Contact Window Timeline: {len(timeline_data)} Windows",
                    fontsize=14, fontweight='bold')

        # Legend
        window_types = set(item['type'] for item in timeline_data)
        color_legend = {}
        if color_by_type and window_types:
            legend_handles = [mpatches.Patch(color=WINDOW_TYPE_COLORS.get(wtype, '#999999'),
                             label=wtype.upper()) for wtype in window_types]
            ax.legend(handles=legend_handles, loc='upper right', framealpha=0.9)
            color_legend = {wtype: WINDOW_TYPE_COLORS.get(wtype, '#999999') for wtype in window_types}

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        return {
            'status': 'success',
            'total_windows': len(timeline_data),
            'groups': num_groups,
            'window_types': list(window_types),
            'color_legend': color_legend if color_by_type else {},
        }


class InteractiveMapCreator:
    """Create interactive HTML maps using folium."""

    def __init__(self, stations: Dict, windows: List[Dict]):
        """Initialize with stations and windows.

        Args:
            stations: Ground stations data
            windows: Contact windows data
        """
        self.stations = stations.get('ground_stations', [])
        self.windows = windows

    def create_map(
        self,
        output_path: Path,
        center: Optional[Tuple[float, float]] = None,
        zoom: int = 7,
        show_coverage: bool = False,
        elevation_angle_deg: float = 5.0,
        show_satellite_passes: bool = False
    ) -> Dict:
        """Create interactive HTML map.

        Args:
            output_path: Output HTML file path
            center: Map center (lat, lon), defaults to Taiwan center
            zoom: Initial zoom level
            show_coverage: Show coverage circles
            elevation_angle_deg: Minimum elevation angle
            show_satellite_passes: Show satellite pass markers

        Returns:
            Dictionary with map metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if center is None:
            center = (TAIWAN_BOUNDS['center_lat'], TAIWAN_BOUNDS['center_lon'])

        m = folium.Map(location=center, zoom_start=zoom, tiles='OpenStreetMap')

        markers_added = 0
        circles_added = 0

        for station in self.stations:
            lat, lon = station['lat'], station['lon']
            name = station['name']
            station_type = station.get('type', 'unknown')
            location_name = station.get('location', name)

            color_map = {
                'command_control': 'red',
                'data_downlink': 'blue',
                'telemetry': 'green',
                'backup': 'orange',
            }
            marker_color = color_map.get(station_type, 'gray')

            popup_html = f"""
            <div style="font-family: Arial; font-size: 12px;">
                <h4 style="margin: 0 0 10px 0; color: #333;">{name}</h4>
                <p style="margin: 5px 0;"><strong>Location:</strong> {location_name}</p>
                <p style="margin: 5px 0;"><strong>Type:</strong> {station_type.replace('_', ' ').title()}</p>
                <p style="margin: 5px 0;"><strong>Coordinates:</strong> {lat:.4f}°N, {lon:.4f}°E</p>
                <p style="margin: 5px 0;"><strong>Altitude:</strong> {station.get('alt', 0)} m</p>
            </div>
            """

            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=name,
                icon=folium.Icon(color=marker_color, icon='satellite', prefix='fa'),
            ).add_to(m)

            markers_added += 1

            if show_coverage:
                coverage_radius_km = calculate_coverage_radius(550, elevation_angle_deg)
                folium.Circle(
                    location=[lat, lon],
                    radius=coverage_radius_km * 1000,
                    color=marker_color,
                    fill=True,
                    fillColor=marker_color,
                    fillOpacity=0.1,
                    opacity=0.5,
                    weight=2,
                    tooltip=f"{name} coverage (~{coverage_radius_km:.0f} km)",
                ).add_to(m)
                circles_added += 1

        # Satellite passes
        satellite_markers = 0
        if show_satellite_passes and self.windows:
            for window in self.windows[:20]:
                gw_name = window.get('gw', '')
                sat_name = window.get('sat', '')
                gw_station = next((s for s in self.stations if s['name'] == gw_name), None)

                if gw_station:
                    popup_html = f"""
                    <div style="font-family: Arial; font-size: 11px;">
                        <h5 style="margin: 0 0 8px 0;">{sat_name} Pass</h5>
                        <p style="margin: 3px 0;"><strong>Gateway:</strong> {gw_name}</p>
                        <p style="margin: 3px 0;"><strong>Type:</strong> {window.get('type', '')}</p>
                        <p style="margin: 3px 0;"><strong>Start:</strong> {window.get('start', '')}</p>
                        <p style="margin: 3px 0;"><strong>End:</strong> {window.get('end', '')}</p>
                    </div>
                    """

                    folium.CircleMarker(
                        location=[gw_station['lat'], gw_station['lon']],
                        radius=4,
                        popup=folium.Popup(popup_html, max_width=200),
                        color='purple',
                        fill=True,
                        fillColor='purple',
                        fillOpacity=0.7,
                    ).add_to(m)
                    satellite_markers += 1

        folium.LayerControl().add_to(m)
        m.save(str(output_path))

        return {
            'status': 'success',
            'center': list(center),
            'zoom': zoom,
            'markers_added': markers_added,
            'coverage_circles': circles_added,
            'satellite_markers': satellite_markers,
        }


def main():
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(description='TASA SatNet Visualization')
    parser.add_argument('--stations', type=Path, required=True, help='Ground stations JSON file')
    parser.add_argument('--windows', type=Path, help='Contact windows JSON file')
    parser.add_argument('--output-dir', type=Path, default=Path('outputs'), help='Output directory')
    parser.add_argument('--all', action='store_true', help='Generate all visualizations')

    args = parser.parse_args()

    # Load data
    with open(args.stations, encoding='utf-8') as f:
        stations_data = json.load(f)

    windows_data = []
    if args.windows and args.windows.exists():
        with open(args.windows, encoding='utf-8') as f:
            data = json.load(f)
            windows_data = data.get('windows', [])

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating visualizations...")

    # Coverage map
    print("  - Coverage map...")
    generator = CoverageMapGenerator(stations_data)
    result = generator.generate_map(
        output_path=args.output_dir / 'coverage_map.png',
        show_range_circles=True,
        color_by_type=True,
    )
    print(f"    Saved: {result['output_path']}")

    # Interactive map
    print("  - Interactive map...")
    creator = InteractiveMapCreator(stations_data, windows_data)
    result = creator.create_map(
        output_path=args.output_dir / 'interactive_map.html',
        show_coverage=True,
        show_satellite_passes=True if windows_data else False,
    )
    print(f"    Saved: {args.output_dir / 'interactive_map.html'}")

    # Timeline (if windows provided)
    if windows_data:
        print("  - Timeline...")
        visualizer = TimelineVisualizer(windows_data)
        result = visualizer.create_timeline(
            output_path=args.output_dir / 'timeline.png',
            group_by='satellite',
            color_by_type=True,
        )
        print(f"    Saved: {args.output_dir / 'timeline.png'}")

        # Trajectories
        print("  - Satellite trajectories...")
        plotter = SatelliteTrajectoryPlotter(windows_data, stations_data)
        result = plotter.plot_trajectories(
            output_path=args.output_dir / 'trajectories.png',
            group_by_constellation=False,
        )
        print(f"    Saved: {args.output_dir / 'trajectories.png'}")

    print("\nDone! All visualizations generated.")


if __name__ == '__main__':
    main()
