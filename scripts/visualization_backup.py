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
        # TDD stub - to be implemented
        raise NotImplementedError("SatelliteTrajectoryPlotter.plot_trajectories() not implemented yet (TDD)")


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
        # TDD stub - to be implemented
        raise NotImplementedError("TimelineVisualizer.create_timeline() not implemented yet (TDD)")


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
        show_coverage: bool = False,
        elevation_angle_deg: float = 5.0,
        show_satellite_passes: bool = False
    ) -> Dict:
        """Create interactive HTML map.

        Args:
            output_path: Output HTML file path
            show_coverage: Show coverage circles
            elevation_angle_deg: Minimum elevation angle
            show_satellite_passes: Show satellite pass markers

        Returns:
            Dictionary with map metadata
        """
        # TDD stub - to be implemented
        raise NotImplementedError("InteractiveMapCreator.create_map() not implemented yet (TDD)")


def main():
    """CLI interface for visualization tools."""
    import argparse

    ap = argparse.ArgumentParser(description="Satellite visualization tools")
    ap.add_argument("--mode", choices=['coverage', 'trajectory', 'timeline', 'interactive'],
                    required=True, help="Visualization mode")
    ap.add_argument("--stations", type=Path, help="Ground stations JSON file")
    ap.add_argument("--windows", type=Path, help="Contact windows JSON file")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output file")

    args = ap.parse_args()

    print(f"Visualization mode: {args.mode}")
    print(f"Output: {args.output}")
    print("Not implemented yet (TDD stub)")

    return 1


if __name__ == "__main__":
    exit(main())
