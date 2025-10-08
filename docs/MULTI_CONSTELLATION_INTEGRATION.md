# Multi-Constellation Integration Guide

## Overview

The TASA SatNet Pipeline supports multiple satellite constellations (GPS, Iridium, OneWeb, Starlink, Globalstar, O3B) with conflict detection, priority-based scheduling, and per-constellation metrics tracking.

## Architecture

### Components

1. **ConstellationManager** (`scripts/constellation_manager.py`)
   - Manages multiple satellite constellations
   - Detects frequency conflicts
   - Handles priority-based scheduling
   - Exports NS-3 scenarios

2. **Extended ScenarioGenerator** (`scripts/gen_scenario.py`)
   - Supports multi-constellation metadata
   - Constellation-specific processing delays
   - Frequency band tracking
   - Priority-based link generation

3. **Extended MetricsCalculator** (`scripts/metrics.py`)
   - Per-constellation metrics
   - Constellation-specific latency adjustments
   - Aggregated statistics per constellation

4. **Multi-Constellation Tools** (`scripts/multi_constellation.py`)
   - TLE file merging
   - Constellation identification
   - Window calculation
   - Conflict detection
   - Priority scheduling

## Supported Constellations

| Constellation | Frequency Band | Priority | Processing Delay | Min Elevation |
|---------------|---------------|----------|------------------|---------------|
| GPS           | L-band        | High     | 2.0 ms          | 5°            |
| Iridium       | Ka-band       | Medium   | 8.0 ms          | 8°            |
| OneWeb        | Ku-band       | Low      | 6.0 ms          | 10°           |
| Starlink      | Ka-band       | Low      | 5.0 ms          | 10°           |
| Globalstar    | L-band        | Medium   | 7.0 ms          | 10°           |
| O3B           | Ka-band       | Medium   | 6.5 ms          | 15°           |

## Quick Start

### 1. Merge TLE Files

```bash
python scripts/multi_constellation.py merge \
    data/gps.tle data/iridium.tle data/starlink.tle \
    -o data/merged.tle
```

### 2. Calculate Contact Windows

```bash
python scripts/multi_constellation.py windows \
    data/merged.tle \
    --stations data/taiwan_ground_stations.json \
    --start "2024-10-08T00:00:00" \
    --end "2024-10-08T23:59:59" \
    --min-elevation 10.0 \
    -o data/multi_windows.json
```

### 3. Detect Conflicts

```bash
python scripts/multi_constellation.py conflicts \
    data/multi_windows.json \
    -o data/conflicts.json
```

### 4. Priority Scheduling

```bash
python scripts/multi_constellation.py schedule \
    data/multi_windows.json \
    -o data/schedule.json
```

### 5. Generate NS-3 Scenario

```bash
python scripts/gen_scenario.py \
    data/multi_windows.json \
    --mode transparent \
    --constellation-config config/multi_constellation_config.json \
    -o config/multi_scenario.json
```

### 6. Compute Metrics

```bash
python scripts/metrics.py \
    config/multi_scenario.json \
    -o reports/multi_metrics.csv \
    --summary reports/multi_summary.json
```

## Complete Workflow Example

```bash
# Run the complete workflow script
python examples/multi_constellation_workflow.py \
    --windows data/multi_windows.json \
    --output-dir results/multi_constellation \
    --mode transparent
```

This will generate:
- `conflicts.json` - Frequency conflict details
- `schedule.json` - Scheduled and rejected windows
- `scenario.json` - NS-3 simulation scenario
- `metrics.csv` - Per-session metrics
- `summary.json` - Aggregated statistics
- `constellation_stats.json` - Per-constellation statistics

## Pipeline Integration

### Full Pipeline

```bash
# Step 1: Merge TLE files
python scripts/multi_constellation.py pipeline \
    data/gps.tle data/iridium.tle \
    --stations data/taiwan_ground_stations.json \
    --start "2024-10-08T00:00:00" \
    --end "2024-10-08T23:59:59" \
    -o data/pipeline_result.json
```

### Using ConstellationManager

```python
from scripts.constellation_manager import ConstellationManager

# Create manager
manager = ConstellationManager()

# Load windows
manager.load_windows_from_json(Path('data/multi_windows.json'))

# Detect conflicts
conflicts = manager.detect_conflicts()
print(f"Found {len(conflicts)} conflicts")

# Schedule with priorities
schedule = manager.get_scheduling_order()
print(f"Scheduled: {len(schedule['scheduled'])}")
print(f"Rejected: {len(schedule['rejected'])}")

# Get statistics
stats = manager.get_constellation_stats()
for constellation, stat in stats.items():
    print(f"{constellation}: {stat['scheduling_efficiency']:.1f}% efficiency")

# Export to NS-3
manager.export_to_ns3_scenario(
    Path('config/scenario.json'),
    mode='transparent'
)
```

## Conflict Detection

### Frequency Conflicts

Conflicts occur when:
1. Same ground station
2. Same frequency band
3. Overlapping time windows

Example output:
```json
{
  "type": "frequency_conflict",
  "window1": "IRIDIUM-1",
  "window2": "STARLINK-1",
  "constellation1": "Iridium",
  "constellation2": "Starlink",
  "frequency_band": "Ka-band",
  "ground_station": "TAIPEI",
  "overlap_start": "2024-10-08T10:05:00Z",
  "overlap_end": "2024-10-08T10:10:00Z"
}
```

### Priority Resolution

Windows are scheduled in priority order:
1. **High priority** (GPS) - scheduled first
2. **Medium priority** (Iridium, Globalstar, O3B)
3. **Low priority** (OneWeb, Starlink)

Conflicting lower-priority windows are rejected.

## Per-Constellation Metrics

### Summary Statistics

```json
{
  "constellation_stats": {
    "GPS": {
      "sessions": 10,
      "latency": {
        "mean_ms": 45.23,
        "min_ms": 42.10,
        "max_ms": 48.56,
        "p95_ms": 47.89
      },
      "throughput": {
        "mean_mbps": 38.45,
        "min_mbps": 35.20,
        "max_mbps": 40.00
      },
      "total_duration_sec": 3600
    }
  }
}
```

### CSV Export

The metrics CSV includes constellation metadata:

```csv
source,target,window_type,start,end,duration_sec,latency_total_ms,latency_rtt_ms,throughput_mbps,utilization_percent,mode,constellation,frequency_band,priority
GPS-1,TAIPEI,cmd,2024-10-08T10:00:00Z,2024-10-08T10:10:00Z,600,45.23,90.46,38.45,76.9,transparent,GPS,L-band,high
IRIDIUM-1,TAIPEI,xband,2024-10-08T10:15:00Z,2024-10-08T10:25:00Z,600,52.34,104.68,39.20,78.4,transparent,Iridium,Ka-band,medium
```

## Configuration

### Constellation Constants

Edit `config/constants.py` to customize:

```python
class ConstellationConstants:
    CONSTELLATION_PROCESSING_DELAYS = {
        'GPS': 2.0,
        'Iridium': 8.0,
        # ... add more
    }

    MIN_ELEVATION_ANGLES = {
        'GPS': 5.0,
        'Iridium': 8.0,
        # ... add more
    }
```

### Frequency Bands

Edit `scripts/multi_constellation.py`:

```python
FREQUENCY_BANDS = {
    'GPS': 'L-band',
    'Iridium': 'Ka-band',
    # ... add more
}
```

### Priority Levels

```python
PRIORITY_LEVELS = {
    'GPS': 'high',
    'Iridium': 'medium',
    'OneWeb': 'low',
    # ... add more
}
```

## Testing

Run the integration tests:

```bash
# Test all constellation integration functionality
pytest tests/test_constellation_integration.py -v

# Test specific functionality
pytest tests/test_constellation_integration.py::TestMultiConstellationScenarioGeneration -v
pytest tests/test_constellation_integration.py::TestConflictDetectionIntegration -v
pytest tests/test_constellation_integration.py::TestPriorityScheduling -v
pytest tests/test_constellation_integration.py::TestMetricsWithConstellations -v
```

## API Reference

### ConstellationManager

```python
class ConstellationManager:
    def add_constellation(name, satellites, frequency_band=None, priority=None, min_elevation=None)
    def load_windows_from_json(windows_file: Path) -> int
    def detect_conflicts(windows: Optional[List[Dict]] = None) -> List[Dict]
    def get_scheduling_order(windows: Optional[List[Dict]] = None) -> Dict
    def get_constellation_stats() -> Dict
    def export_to_ns3_scenario(output_file: Path, include_rejected: bool = False, mode: str = 'transparent') -> Dict
    def get_frequency_band_usage() -> Dict[str, int]
    def get_priority_distribution() -> Dict[str, int]
```

### ScenarioGenerator

```python
class ScenarioGenerator:
    def __init__(mode: str = "transparent", enable_constellation_support: bool = True)
    def generate(windows_data: Dict, skip_validation: bool = False, constellation_config: Optional[Path] = None) -> Dict
```

### MetricsCalculator

```python
class MetricsCalculator:
    def __init__(scenario: Dict, skip_validation: bool = False, enable_constellation_metrics: bool = True)
    def compute_all_metrics() -> List[Dict]
    def generate_summary() -> Dict
    def export_csv(output_path: Path)
```

## Troubleshooting

### Common Issues

1. **TLE Processor Not Available**
   - Install skyfield: `pip install skyfield`
   - Check TLE file format (3-line format required)

2. **No Conflicts Detected**
   - Verify windows overlap in time
   - Check frequency band mapping
   - Ensure same ground station

3. **All Windows Rejected**
   - Review priority levels
   - Check for conflicting windows
   - Verify frequency band assignments

### Debug Mode

Enable verbose logging:

```bash
python scripts/constellation_manager.py \
    data/multi_windows.json \
    -o config/scenario.json \
    --stats
```

## Performance

### Benchmarks

- **Window calculation**: ~100 windows/second
- **Conflict detection**: O(n²) where n = windows per station/band
- **Scheduling**: O(n log n) sorting + O(n²) conflict checking
- **Metrics**: ~1000 sessions/second

### Optimization Tips

1. Use lower time step for TLE calculations (e.g., 60s instead of 10s)
2. Filter by minimum elevation early
3. Batch process multiple stations in parallel
4. Use `--skip-validation` for production runs (after testing)

## Examples

See the `examples/` directory for:
- `multi_constellation_workflow.py` - Complete workflow example
- Additional constellation-specific examples

## Further Reading

- [Multi-Constellation README](../scripts/README_MULTI_CONSTELLATION.md)
- [TLE Processing Guide](./TLE_INTEGRATION.md)
- [NS-3 Scenario Format](./NS3_SCENARIO_FORMAT.md)
- [Metrics Visualization](./METRICS_VISUALIZATION.md)

## Contributing

When adding new constellations:

1. Add to `CONSTELLATION_PATTERNS` in `multi_constellation.py`
2. Add frequency band to `FREQUENCY_BANDS`
3. Add priority level to `PRIORITY_LEVELS`
4. Add processing delay to `ConstellationConstants`
5. Add minimum elevation to `ConstellationConstants`
6. Update tests in `test_multi_constellation.py`
7. Update this documentation

## License

See LICENSE file in repository root.
