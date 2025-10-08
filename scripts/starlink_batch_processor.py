#!/usr/bin/env python3
"""
Starlink 100 Satellite Batch Processing Tool

Processes visibility windows for up to 100 Starlink satellites across multiple
ground stations using parallel processing and progress reporting.

Features:
- Extract subset of satellites from TLE file
- Parallel window calculation across multiple stations
- Progress reporting with tqdm
- Checkpoint/resume capability
- Coverage statistics computation
- Memory-efficient processing

Performance targets:
- 100 satellites × 6 stations < 60 seconds
- Memory usage < 1 GB
- Support for interrupt/resume

Usage:
    python starlink_batch_processor.py --tle data/starlink.tle \
        --stations data/stations.json \
        --count 100 \
        --start 2025-10-08T00:00:00Z \
        --end 2025-10-09T00:00:00Z \
        --output data/starlink_windows.json
"""

from __future__ import annotations
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from multiprocessing import Pool, cpu_count
import traceback

import numpy as np
from sgp4.api import Satrec, jday
from tqdm import tqdm

# Import from existing tle_windows.py
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).parent))

from tle_windows import (
    Site, gmst, teme_to_ecef, geodetic_to_ecef,
    elevation_deg, dt_range
)

# ============================================================================
# Configuration
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SatelliteData:
    """Satellite TLE data."""
    name: str
    line1: str
    line2: str
    satrec: Optional[Satrec] = None

    def __post_init__(self):
        """Initialize SGP4 satellite record."""
        if self.satrec is None and self.line1 and self.line2:
            try:
                self.satrec = Satrec.twoline2rv(self.line1, self.line2)
            except Exception as e:
                logger.warning(f"Failed to initialize {self.name}: {e}")


@dataclass
class VisibilityWindow:
    """Visibility window data."""
    satellite: str
    station: str
    start: str
    end: str
    duration_sec: float
    elevation_max: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


# ============================================================================
# Core Functions
# ============================================================================

def extract_starlink_subset(tle_file: Path, count: int = 100) -> List[Dict[str, str]]:
    """
    Extract subset of satellites from TLE file.

    Args:
        tle_file: Path to TLE file
        count: Number of satellites to extract (default: 100)

    Returns:
        List of satellite dictionaries with name, line1, line2

    Raises:
        FileNotFoundError: If TLE file doesn't exist
        ValueError: If TLE format is invalid

    Examples:
        >>> satellites = extract_starlink_subset(Path("starlink.tle"), count=10)
        >>> len(satellites)
        10
        >>> satellites[0]['name']
        'STARLINK-1008'
    """
    if not tle_file.exists():
        raise FileNotFoundError(f"TLE file not found: {tle_file}")

    logger.info(f"Reading TLE file: {tle_file}")
    lines = tle_file.read_text(encoding='utf-8', errors='ignore').strip().splitlines()

    satellites = []
    i = 0

    while i < len(lines) and len(satellites) < count:
        # Skip empty lines
        while i < len(lines) and not lines[i].strip():
            i += 1

        if i >= len(lines):
            break

        # Check if this is a 3-line TLE (name + line1 + line2)
        if i + 2 < len(lines):
            line0 = lines[i].strip()
            line1 = lines[i + 1].strip()
            line2 = lines[i + 2].strip()

            # Validate TLE format
            if line1.startswith('1 ') and line2.startswith('2 '):
                # Has name line
                if not line0.startswith('1 ') and not line0.startswith('2 '):
                    name = line0
                else:
                    name = f"SAT-{len(satellites) + 1}"

                satellites.append({
                    'name': name,
                    'line1': line1,
                    'line2': line2
                })
                i += 3
            elif i + 1 < len(lines) and line0.startswith('1 ') and line1.startswith('2 '):
                # 2-line TLE without name
                satellites.append({
                    'name': f"SAT-{len(satellites) + 1}",
                    'line1': line0,
                    'line2': line1
                })
                i += 2
            else:
                i += 1
        else:
            break

    logger.info(f"Extracted {len(satellites)} satellites (requested: {count})")
    return satellites


def calculate_single_station_windows(args: tuple) -> List[Dict[str, Any]]:
    """
    Calculate visibility windows for a single station (for parallel processing).

    Args:
        args: Tuple of (satellites, station, time_range, min_elevation, step_sec)

    Returns:
        List of visibility windows for the station
    """
    satellites, station, time_range, min_elevation, step_sec = args

    try:
        station_name = station['name']
        site = Site(station['lat'], station['lon'], station.get('alt', 0))
        site_ecef = geodetic_to_ecef(site.lat, site.lon, site.alt)

        # Parse time range
        t0 = datetime.fromisoformat(time_range['start'].replace('Z', '+00:00'))
        t1 = datetime.fromisoformat(time_range['end'].replace('Z', '+00:00'))
        t0 = t0.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        t1 = t1.astimezone(timezone.utc).replace(tzinfo=timezone.utc)

        windows = []

        # Process each satellite
        for sat_data in satellites:
            try:
                sat = Satrec.twoline2rv(sat_data['line1'], sat_data['line2'])
                sat_name = sat_data['name']

                in_contact = False
                current_window = None
                max_elev = 0.0

                for t in dt_range(t0, t1, step_sec):
                    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute,
                                 t.second + t.microsecond * 1e-6)
                    e, r, v = sat.sgp4(jd, fr)

                    if e != 0:
                        continue

                    r_ecef = teme_to_ecef(np.array(r, float), t)
                    elev = elevation_deg(r_ecef, site_ecef, site.lat, site.lon)

                    if elev >= min_elevation:
                        max_elev = max(max_elev, elev)

                        if not in_contact:
                            # Start new window
                            in_contact = True
                            current_window = {
                                'satellite': sat_name,
                                'station': station_name,
                                'start': t.isoformat().replace('+00:00', 'Z'),
                                'end': None,
                                'elevation_max': elev
                            }
                    elif in_contact:
                        # End current window
                        in_contact = False
                        current_window['end'] = t.isoformat().replace('+00:00', 'Z')
                        current_window['elevation_max'] = max_elev

                        # Calculate duration
                        start_dt = datetime.fromisoformat(current_window['start'].replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(current_window['end'].replace('Z', '+00:00'))
                        current_window['duration_sec'] = (end_dt - start_dt).total_seconds()

                        windows.append(current_window)
                        current_window = None
                        max_elev = 0.0

                # Handle window extending beyond time range
                if in_contact and current_window:
                    current_window['end'] = t1.isoformat().replace('+00:00', 'Z')
                    current_window['elevation_max'] = max_elev

                    start_dt = datetime.fromisoformat(current_window['start'].replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(current_window['end'].replace('Z', '+00:00'))
                    current_window['duration_sec'] = (end_dt - start_dt).total_seconds()

                    windows.append(current_window)

            except Exception as e:
                logger.warning(f"Error processing {sat_data['name']} for {station_name}: {e}")
                continue

        return windows

    except Exception as e:
        logger.error(f"Error in station processing: {e}")
        logger.error(traceback.format_exc())
        return []


def calculate_batch_windows(
    satellites: List[Dict[str, str]],
    stations: List[Dict[str, Any]],
    time_range: Dict[str, str],
    min_elevation: float = 10.0,
    step_sec: int = 30,
    parallel: bool = True,
    show_progress: bool = False
) -> List[Dict[str, Any]]:
    """
    Calculate visibility windows for multiple satellites and stations.

    Args:
        satellites: List of satellite TLE data
        stations: List of ground station data
        time_range: Dictionary with 'start' and 'end' ISO timestamps
        min_elevation: Minimum elevation angle in degrees (default: 10.0)
        step_sec: Time step in seconds (default: 30)
        parallel: Use parallel processing (default: True)
        show_progress: Show progress bar (default: False)

    Returns:
        List of visibility windows

    Raises:
        ValueError: If time range is invalid

    Examples:
        >>> windows = calculate_batch_windows(
        ...     satellites=[{'name': 'SAT1', 'line1': '...', 'line2': '...'}],
        ...     stations=[{'name': 'GS1', 'lat': 25.0, 'lon': 121.0, 'alt': 0}],
        ...     time_range={'start': '2025-10-08T00:00:00Z', 'end': '2025-10-08T06:00:00Z'}
        ... )
    """
    # Validate time range
    start = datetime.fromisoformat(time_range['start'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(time_range['end'].replace('Z', '+00:00'))

    if end <= start:
        raise ValueError(f"End time must be after start time: {start} >= {end}")

    if not satellites:
        logger.warning("No satellites provided")
        return []

    if not stations:
        logger.warning("No stations provided")
        return []

    logger.info(f"Calculating windows for {len(satellites)} satellites × {len(stations)} stations")
    logger.info(f"Time range: {time_range['start']} to {time_range['end']}")

    # Prepare arguments for parallel processing
    args_list = [
        (satellites, station, time_range, min_elevation, step_sec)
        for station in stations
    ]

    all_windows = []

    if parallel and len(stations) > 1:
        # Use multiprocessing
        num_workers = min(cpu_count(), len(stations))
        logger.info(f"Using {num_workers} parallel workers")

        with Pool(processes=num_workers) as pool:
            if show_progress:
                results = list(tqdm(
                    pool.imap(calculate_single_station_windows, args_list),
                    total=len(args_list),
                    desc="Processing stations"
                ))
            else:
                results = pool.map(calculate_single_station_windows, args_list)

        # Flatten results
        for station_windows in results:
            all_windows.extend(station_windows)
    else:
        # Sequential processing
        iterator = args_list
        if show_progress:
            iterator = tqdm(iterator, desc="Processing stations")

        for args in iterator:
            station_windows = calculate_single_station_windows(args)
            all_windows.extend(station_windows)

    logger.info(f"Calculated {len(all_windows)} total windows")
    return all_windows


def merge_station_windows(window_data_list: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Merge window data from multiple stations.

    Args:
        window_data_list: List of window lists (one per station)

    Returns:
        Merged window data with metadata

    Examples:
        >>> merged = merge_station_windows([
        ...     [{'satellite': 'SAT1', 'station': 'GS1', 'start': '...', 'end': '...'}],
        ...     [{'satellite': 'SAT2', 'station': 'GS2', 'start': '...', 'end': '...'}]
        ... ])
    """
    all_windows = []

    for windows in window_data_list:
        all_windows.extend(windows)

    # Sort by start time
    all_windows.sort(key=lambda w: w['start'])

    # Extract metadata
    stations = set(w['station'] for w in all_windows)
    satellites = set(w['satellite'] for w in all_windows)

    # Calculate time range
    time_range = {}
    if all_windows:
        time_range = {
            'start': min(w['start'] for w in all_windows),
            'end': max(w['end'] for w in all_windows)
        }

    merged = {
        'meta': {
            'total_windows': len(all_windows),
            'station_count': len(stations),
            'total_satellites': len(satellites),
            'time_range': time_range,
            'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        },
        'stations': sorted(list(stations)),
        'windows': all_windows
    }

    return merged


def compute_coverage_stats(
    merged_windows: Dict[str, Any],
    stations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compute coverage statistics from merged windows.

    Args:
        merged_windows: Merged window data
        stations: List of station configurations

    Returns:
        Coverage statistics dictionary

    Examples:
        >>> stats = compute_coverage_stats(merged_windows, stations)
        >>> stats['total_windows']
        42
        >>> stats['coverage_by_station']['HSINCHU']['window_count']
        15
    """
    windows = merged_windows.get('windows', [])

    # Initialize stats
    stats = {
        'total_windows': len(windows),
        'stations': len(stations),
        'satellites': merged_windows['meta'].get('total_satellites', 0),
        'coverage_by_station': {},
        'satellite_distribution': {}
    }

    # Calculate per-station stats
    station_names = [s['name'] for s in stations]

    for station_name in station_names:
        station_windows = [w for w in windows if w['station'] == station_name]

        if station_windows:
            total_duration = sum(w['duration_sec'] for w in station_windows)
            avg_duration = total_duration / len(station_windows)
            unique_satellites = len(set(w['satellite'] for w in station_windows))

            # Calculate time coverage percentage
            if merged_windows['meta'].get('time_range'):
                time_range = merged_windows['meta']['time_range']
                start = datetime.fromisoformat(time_range['start'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(time_range['end'].replace('Z', '+00:00'))
                total_time_sec = (end - start).total_seconds()
                time_coverage_pct = (total_duration / total_time_sec * 100) if total_time_sec > 0 else 0
            else:
                time_coverage_pct = 0

            stats['coverage_by_station'][station_name] = {
                'window_count': len(station_windows),
                'total_duration_sec': total_duration,
                'avg_duration_sec': avg_duration,
                'satellite_count': unique_satellites,
                'time_coverage_pct': round(time_coverage_pct, 2)
            }
        else:
            stats['coverage_by_station'][station_name] = {
                'window_count': 0,
                'total_duration_sec': 0,
                'avg_duration_sec': 0,
                'satellite_count': 0,
                'time_coverage_pct': 0
            }

    # Calculate satellite distribution
    for window in windows:
        sat = window['satellite']
        stats['satellite_distribution'][sat] = stats['satellite_distribution'].get(sat, 0) + 1

    return stats


# ============================================================================
# Main Processor Class
# ============================================================================

class StarlinkBatchProcessor:
    """
    Main batch processor for Starlink satellite visibility windows.

    Attributes:
        tle_file: Path to TLE file
        stations_file: Path to stations JSON file
        satellite_count: Number of satellites to process
        output_file: Output file path
        checkpoint_file: Checkpoint file for resume capability

    Examples:
        >>> processor = StarlinkBatchProcessor(
        ...     tle_file=Path("starlink.tle"),
        ...     stations_file=Path("stations.json"),
        ...     satellite_count=100
        ... )
        >>> result = processor.run(
        ...     start_time='2025-10-08T00:00:00Z',
        ...     end_time='2025-10-09T00:00:00Z'
        ... )
    """

    def __init__(
        self,
        tle_file: Path,
        stations_file: Path,
        satellite_count: int = 100,
        output_file: Optional[Path] = None,
        checkpoint_file: Optional[Path] = None
    ):
        """Initialize batch processor."""
        self.tle_file = tle_file
        self.stations_file = stations_file
        self.satellite_count = satellite_count
        self.output_file = output_file or Path("data/starlink_batch_windows.json")
        self.checkpoint_file = checkpoint_file or Path("data/checkpoint.json")

        # Load stations
        with self.stations_file.open(encoding='utf-8') as f:
            data = json.load(f)
            self.stations = data.get('ground_stations', [])

        logger.info(f"Initialized processor: {len(self.stations)} stations, {satellite_count} satellites")

    def save_checkpoint(self, data: Dict[str, Any]):
        """Save processing checkpoint."""
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with self.checkpoint_file.open('w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved checkpoint: {self.checkpoint_file}")

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load processing checkpoint."""
        if self.checkpoint_file.exists():
            with self.checkpoint_file.open() as f:
                return json.load(f)
        return None

    def can_resume(self) -> bool:
        """Check if processing can be resumed."""
        return self.checkpoint_file.exists()

    def run(
        self,
        start_time: str,
        end_time: str,
        min_elevation: float = 10.0,
        step_sec: int = 30,
        show_progress: bool = True,
        track_memory: bool = False
    ) -> Dict[str, Any]:
        """
        Run full batch processing pipeline.

        Args:
            start_time: Start time (ISO 8601)
            end_time: End time (ISO 8601)
            min_elevation: Minimum elevation angle (degrees)
            step_sec: Time step (seconds)
            show_progress: Show progress bars
            track_memory: Track memory usage

        Returns:
            Result dictionary with status and statistics
        """
        import psutil
        import os

        start_proc_time = time.time()
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        try:
            # Step 1: Extract satellites
            logger.info("Step 1: Extracting satellite subset")
            satellites = extract_starlink_subset(self.tle_file, count=self.satellite_count)

            # Step 2: Calculate windows
            logger.info("Step 2: Calculating visibility windows")
            time_range = {'start': start_time, 'end': end_time}

            windows = calculate_batch_windows(
                satellites=satellites,
                stations=self.stations,
                time_range=time_range,
                min_elevation=min_elevation,
                step_sec=step_sec,
                parallel=True,
                show_progress=show_progress
            )

            # Step 3: Merge and format
            logger.info("Step 3: Merging windows")
            merged = merge_station_windows([windows])

            # Step 4: Compute statistics
            logger.info("Step 4: Computing coverage statistics")
            stats = compute_coverage_stats(merged, self.stations)

            # Step 5: Save output
            logger.info("Step 5: Saving output")
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            with self.output_file.open('w') as f:
                json.dump(merged, f, indent=2)

            # Calculate performance metrics
            duration = time.time() - start_proc_time
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            peak_memory = final_memory

            result = {
                'status': 'success',
                'output_file': str(self.output_file),
                'statistics': stats,
                'performance': {
                    'duration_sec': round(duration, 2),
                    'satellites_processed': len(satellites),
                    'stations_processed': len(self.stations),
                    'windows_generated': len(windows)
                }
            }

            if track_memory:
                result['statistics']['peak_memory_mb'] = round(peak_memory, 2)
                result['statistics']['memory_delta_mb'] = round(peak_memory - initial_memory, 2)

            logger.info(f"Processing complete in {duration:.2f}s")
            logger.info(f"   Generated {len(windows)} windows")
            logger.info(f"   Output: {self.output_file}")

            return result

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            logger.error(traceback.format_exc())

            return {
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            }


# ============================================================================
# CLI Interface
# ============================================================================

def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Starlink 100 Satellite Batch Processor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process 100 satellites for 24 hours
    python starlink_batch_processor.py \\
        --tle data/starlink.tle \\
        --stations data/taiwan_ground_stations.json \\
        --count 100 \\
        --start 2025-10-08T00:00:00Z \\
        --end 2025-10-09T00:00:00Z \\
        --output data/starlink_windows.json

    # Resume from checkpoint
    python starlink_batch_processor.py \\
        --tle data/starlink.tle \\
        --stations data/stations.json \\
        --checkpoint data/checkpoint.json \\
        --resume
        """
    )

    parser.add_argument('--tle', type=Path, required=True,
                       help='TLE file path')
    parser.add_argument('--stations', type=Path, required=True,
                       help='Ground stations JSON file')
    parser.add_argument('--count', type=int, default=100,
                       help='Number of satellites to process (default: 100)')
    parser.add_argument('--start', type=str, required=True,
                       help='Start time (ISO 8601)')
    parser.add_argument('--end', type=str, required=True,
                       help='End time (ISO 8601)')
    parser.add_argument('--output', type=Path,
                       default=Path('data/starlink_batch_windows.json'),
                       help='Output file path')
    parser.add_argument('--min-elev', type=float, default=10.0,
                       help='Minimum elevation angle (degrees, default: 10.0)')
    parser.add_argument('--step', type=int, default=30,
                       help='Time step in seconds (default: 30)')
    parser.add_argument('--checkpoint', type=Path,
                       default=Path('data/checkpoint.json'),
                       help='Checkpoint file for resume')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from checkpoint')
    parser.add_argument('--progress', action='store_true',
                       help='Show progress bars')
    parser.add_argument('--track-memory', action='store_true',
                       help='Track memory usage')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Initialize processor
    processor = StarlinkBatchProcessor(
        tle_file=args.tle,
        stations_file=args.stations,
        satellite_count=args.count,
        output_file=args.output,
        checkpoint_file=args.checkpoint
    )

    # Check resume
    if args.resume and processor.can_resume():
        logger.info("Resume capability detected (not yet implemented)")
        # TODO: Implement resume logic

    # Run processing
    result = processor.run(
        start_time=args.start,
        end_time=args.end,
        min_elevation=args.min_elev,
        step_sec=args.step,
        show_progress=args.progress,
        track_memory=args.track_memory
    )

    if result['status'] == 'success':
        print("\n" + "="*70)
        print("PROCESSING COMPLETE")
        print("="*70)
        print(f"Output file: {result['output_file']}")
        print(f"Duration: {result['performance']['duration_sec']}s")
        print(f"Windows generated: {result['performance']['windows_generated']}")
        print("\nCoverage Statistics:")
        for station, stats in result['statistics']['coverage_by_station'].items():
            print(f"  {station}: {stats['window_count']} windows, "
                  f"{stats['time_coverage_pct']:.1f}% coverage")
        print("="*70 + "\n")
        return 0
    else:
        print("\n" + "="*70)
        print("PROCESSING FAILED")
        print("="*70)
        print(f"Error: {result['error']}")
        print("="*70 + "\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
