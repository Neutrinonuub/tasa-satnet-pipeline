#!/usr/bin/env python3
"""
Constellation Manager for TASA SatNet Pipeline.

This module provides a unified interface for managing multiple satellite
constellations, detecting conflicts, and exporting to NS-3 scenarios.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import dataclass, asdict
import sys

# Add parent directory to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.constants import ConstellationConstants

# Import multi-constellation utilities
try:
    from scripts.multi_constellation import (
        identify_constellation,
        FREQUENCY_BANDS,
        PRIORITY_LEVELS,
        PRIORITY_ORDER,
        detect_conflicts,
        prioritize_scheduling
    )
except ImportError:
    print("Warning: multi_constellation module not available")
    FREQUENCY_BANDS = {}
    PRIORITY_LEVELS = {}
    PRIORITY_ORDER = {'high': 0, 'medium': 1, 'low': 2}


@dataclass
class ConstellationMetadata:
    """Metadata for a satellite constellation."""
    name: str
    satellite_count: int
    frequency_band: str
    priority: str
    min_elevation: float
    processing_delay_ms: float
    windows_count: int = 0


class ConstellationManager:
    """
    Manages multiple satellite constellations with conflict detection
    and scheduling capabilities.
    """

    def __init__(self):
        """Initialize constellation manager."""
        self.constellations: Dict[str, ConstellationMetadata] = {}
        self.satellites: Dict[str, str] = {}  # sat_name -> constellation
        self.windows: List[Dict] = []
        self.conflicts: List[Dict] = []
        self.scheduled_windows: List[Dict] = []
        self.rejected_windows: List[Dict] = []

    def add_constellation(
        self,
        name: str,
        satellites: List[str],
        frequency_band: Optional[str] = None,
        priority: Optional[str] = None,
        min_elevation: Optional[float] = None
    ) -> None:
        """
        Add a constellation to the manager.

        Args:
            name: Constellation name (GPS, Iridium, etc.)
            satellites: List of satellite names
            frequency_band: Override default frequency band
            priority: Override default priority
            min_elevation: Override default minimum elevation
        """
        # Get defaults from configuration
        if frequency_band is None:
            frequency_band = FREQUENCY_BANDS.get(name, 'Unknown')
        if priority is None:
            priority = PRIORITY_LEVELS.get(name, 'low')
        if min_elevation is None:
            min_elevation = ConstellationConstants.MIN_ELEVATION_ANGLES.get(name, 10.0)

        processing_delay = ConstellationConstants.CONSTELLATION_PROCESSING_DELAYS.get(
            name, 10.0
        )

        metadata = ConstellationMetadata(
            name=name,
            satellite_count=len(satellites),
            frequency_band=frequency_band,
            priority=priority,
            min_elevation=min_elevation,
            processing_delay_ms=processing_delay
        )

        self.constellations[name] = metadata

        # Map satellites to constellation
        for sat in satellites:
            self.satellites[sat] = name

    def load_windows_from_json(self, windows_file: Path) -> int:
        """
        Load contact windows from multi-constellation JSON output.

        Args:
            windows_file: Path to windows JSON file

        Returns:
            Number of windows loaded
        """
        with windows_file.open() as f:
            data = json.load(f)

        windows = data.get('windows', [])

        # Auto-detect constellations from windows
        constellation_sats = defaultdict(set)
        for window in windows:
            constellation = window.get('constellation', 'Unknown')
            satellite = window.get('satellite', window.get('sat'))
            if satellite:
                constellation_sats[constellation].add(satellite)

        # Add detected constellations
        for constellation, sats in constellation_sats.items():
            if constellation not in self.constellations:
                self.add_constellation(constellation, list(sats))

        # Update window counts
        for window in windows:
            constellation = window.get('constellation', 'Unknown')
            if constellation in self.constellations:
                self.constellations[constellation].windows_count += 1

        self.windows = windows
        return len(windows)

    def detect_conflicts(self, windows: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Detect frequency conflicts between windows.

        Args:
            windows: Windows to check (default: self.windows)

        Returns:
            List of conflict dictionaries
        """
        if windows is None:
            windows = self.windows

        self.conflicts = detect_conflicts(windows, FREQUENCY_BANDS)
        return self.conflicts

    def get_scheduling_order(
        self,
        windows: Optional[List[Dict]] = None,
        custom_priorities: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Get priority-based scheduling order with conflict resolution.

        Args:
            windows: Windows to schedule (default: self.windows)
            custom_priorities: Override priority levels

        Returns:
            Dict with 'scheduled' and 'rejected' windows
        """
        if windows is None:
            windows = self.windows

        priorities = custom_priorities or PRIORITY_LEVELS
        result = prioritize_scheduling(windows, priorities)

        self.scheduled_windows = result['scheduled']
        self.rejected_windows = result['rejected']

        return result

    def get_constellation_stats(self) -> Dict:
        """
        Get statistics for all constellations.

        Returns:
            Dictionary with per-constellation statistics
        """
        stats = {}

        for name, metadata in self.constellations.items():
            # Count windows by type
            constellation_windows = [
                w for w in self.windows
                if w.get('constellation') == name
            ]

            scheduled_count = len([
                w for w in self.scheduled_windows
                if w.get('constellation') == name
            ])

            rejected_count = len([
                w for w in self.rejected_windows
                if w.get('constellation') == name
            ])

            # Count conflicts involving this constellation
            constellation_conflicts = [
                c for c in self.conflicts
                if c.get('constellation1') == name or c.get('constellation2') == name
            ]

            stats[name] = {
                'metadata': asdict(metadata),
                'total_windows': len(constellation_windows),
                'scheduled_windows': scheduled_count,
                'rejected_windows': rejected_count,
                'conflicts': len(constellation_conflicts),
                'scheduling_efficiency': (
                    scheduled_count / len(constellation_windows) * 100
                    if constellation_windows else 0.0
                )
            }

        return stats

    def export_to_ns3_scenario(
        self,
        output_file: Path,
        include_rejected: bool = False,
        mode: str = 'transparent'
    ) -> Dict:
        """
        Export multi-constellation scenario to NS-3 compatible format.

        Args:
            output_file: Path to output scenario file
            include_rejected: Include rejected windows in output
            mode: Relay mode (transparent or regenerative)

        Returns:
            Scenario dictionary
        """
        # Build topology from all constellations
        satellites = []
        for constellation, metadata in self.constellations.items():
            for sat_name in self.satellites:
                if self.satellites[sat_name] == constellation:
                    satellites.append({
                        'id': sat_name,
                        'type': 'satellite',
                        'constellation': constellation,
                        'frequency_band': metadata.frequency_band,
                        'priority': metadata.priority,
                        'processing_delay_ms': metadata.processing_delay_ms,
                        'orbit': 'LEO'  # Could be enhanced with orbital data
                    })

        # Extract unique gateways
        gateways = set()
        for window in self.windows:
            gw = window.get('ground_station', window.get('gw'))
            if gw:
                gateways.add(gw)

        gateway_list = [
            {
                'id': gw,
                'type': 'gateway',
                'location': gw
            }
            for gw in sorted(gateways)
        ]

        # Build events from scheduled windows (and optionally rejected)
        events = []
        windows_to_process = self.scheduled_windows.copy()
        if include_rejected:
            windows_to_process.extend(self.rejected_windows)

        for window in windows_to_process:
            constellation = window.get('constellation', 'Unknown')

            # Link up event
            events.append({
                'time': window['start'],
                'type': 'link_up',
                'source': window.get('satellite', window.get('sat')),
                'target': window.get('ground_station', window.get('gw')),
                'constellation': constellation,
                'frequency_band': window.get('frequency_band', 'Unknown'),
                'priority': window.get('priority', 'low'),
                'rejected': window in self.rejected_windows
            })

            # Link down event
            events.append({
                'time': window['end'],
                'type': 'link_down',
                'source': window.get('satellite', window.get('sat')),
                'target': window.get('ground_station', window.get('gw')),
                'constellation': constellation,
                'frequency_band': window.get('frequency_band', 'Unknown'),
                'priority': window.get('priority', 'low'),
                'rejected': window in self.rejected_windows
            })

        # Sort events by time
        events.sort(key=lambda e: e['time'])

        # Build scenario
        scenario = {
            'metadata': {
                'name': 'Multi-Constellation Scenario',
                'mode': mode,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'constellations': list(self.constellations.keys()),
                'total_satellites': len(satellites),
                'total_gateways': len(gateway_list),
                'total_conflicts': len(self.conflicts),
                'scheduled_windows': len(self.scheduled_windows),
                'rejected_windows': len(self.rejected_windows)
            },
            'topology': {
                'satellites': satellites,
                'gateways': gateway_list,
                'constellation_stats': self.get_constellation_stats()
            },
            'events': events,
            'conflicts': self.conflicts,
            'parameters': {
                'relay_mode': mode,
                'include_rejected_windows': include_rejected,
                'constellation_processing_enabled': True
            }
        }

        # Write to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open('w') as f:
            json.dump(scenario, f, indent=2)

        return scenario

    def get_frequency_band_usage(self) -> Dict[str, int]:
        """
        Get frequency band usage statistics.

        Returns:
            Dict mapping frequency bands to window counts
        """
        usage = defaultdict(int)
        for window in self.scheduled_windows:
            band = window.get('frequency_band', 'Unknown')
            usage[band] += 1
        return dict(usage)

    def get_priority_distribution(self) -> Dict[str, int]:
        """
        Get priority level distribution.

        Returns:
            Dict mapping priority levels to window counts
        """
        distribution = defaultdict(int)
        for window in self.scheduled_windows:
            priority = window.get('priority', 'low')
            distribution[priority] += 1
        return dict(distribution)


def main():
    """CLI interface for constellation manager."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Constellation Manager for Multi-Constellation Scenarios'
    )
    parser.add_argument('windows_file', type=Path, help='Multi-constellation windows JSON')
    parser.add_argument('-o', '--output', type=Path,
                       default=Path('config/multi_constellation_scenario.json'),
                       help='Output NS-3 scenario file')
    parser.add_argument('--mode', choices=['transparent', 'regenerative'],
                       default='transparent', help='Relay mode')
    parser.add_argument('--include-rejected', action='store_true',
                       help='Include rejected windows in scenario')
    parser.add_argument('--stats', action='store_true',
                       help='Print constellation statistics')

    args = parser.parse_args()

    # Create manager
    manager = ConstellationManager()

    # Load windows
    print(f"Loading windows from {args.windows_file}...")
    count = manager.load_windows_from_json(args.windows_file)
    print(f"Loaded {count} windows")

    # Detect conflicts
    print("\nDetecting conflicts...")
    conflicts = manager.detect_conflicts()
    print(f"Found {len(conflicts)} conflicts")

    # Schedule windows
    print("\nScheduling windows with priority...")
    schedule = manager.get_scheduling_order()
    print(f"Scheduled: {len(schedule['scheduled'])} windows")
    print(f"Rejected: {len(schedule['rejected'])} windows")

    # Export to NS-3 scenario
    print(f"\nExporting to {args.output}...")
    scenario = manager.export_to_ns3_scenario(
        args.output,
        include_rejected=args.include_rejected,
        mode=args.mode
    )

    # Print statistics if requested
    if args.stats:
        print("\n" + "="*60)
        print("CONSTELLATION STATISTICS")
        print("="*60)

        stats = manager.get_constellation_stats()
        for constellation, stat in stats.items():
            print(f"\n{constellation}:")
            print(f"  Satellites: {stat['metadata']['satellite_count']}")
            print(f"  Frequency Band: {stat['metadata']['frequency_band']}")
            print(f"  Priority: {stat['metadata']['priority']}")
            print(f"  Total Windows: {stat['total_windows']}")
            print(f"  Scheduled: {stat['scheduled_windows']}")
            print(f"  Rejected: {stat['rejected_windows']}")
            print(f"  Conflicts: {stat['conflicts']}")
            print(f"  Efficiency: {stat['scheduling_efficiency']:.1f}%")

        print("\n" + "="*60)
        print("FREQUENCY BAND USAGE")
        print("="*60)
        for band, count in manager.get_frequency_band_usage().items():
            print(f"  {band}: {count} windows")

        print("\n" + "="*60)
        print("PRIORITY DISTRIBUTION")
        print("="*60)
        for priority, count in manager.get_priority_distribution().items():
            print(f"  {priority}: {count} windows")

    print(f"\nScenario exported successfully!")
    print(f"Output: {args.output}")

    return 0


if __name__ == "__main__":
    exit(main())
