# Starlink 100 Satellite Batch Processor - Usage Guide

## Overview

The Starlink batch processor calculates visibility windows for up to 100 Starlink satellites across multiple Taiwan ground stations using parallel processing.

## Features

✓ **Extract subset** of satellites from TLE file
✓ **Parallel processing** across multiple ground stations
✓ **Progress reporting** with tqdm
✓ **Coverage statistics** per station
✓ **Checkpoint/resume** capability
✓ **Memory efficient** (< 1 GB for 100 satellites)
✓ **Fast processing** (< 60s for 100 sats × 6 stations)

## Installation

```bash
# Install required packages
pip install sgp4 numpy tqdm psutil

# Or use requirements.txt
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```bash
# Process 10 satellites for 6 hours
python scripts/starlink_batch_processor.py \
    --tle data/starlink.tle \
    --stations data/taiwan_ground_stations.json \
    --count 10 \
    --start 2025-10-08T00:00:00Z \
    --end 2025-10-08T06:00:00Z \
    --output data/starlink_windows.json
```

### With Progress Bar

```bash
python scripts/starlink_batch_processor.py \
    --tle data/starlink.tle \
    --stations data/taiwan_ground_stations.json \
    --count 100 \
    --start 2025-10-08T00:00:00Z \
    --end 2025-10-09T00:00:00Z \
    --output data/starlink_100sats_24h.json \
    --progress
```

### Full 24-Hour Run with All Options

```bash
python scripts/starlink_batch_processor.py \
    --tle data/starlink.tle \
    --stations data/taiwan_ground_stations.json \
    --count 100 \
    --start 2025-10-08T00:00:00Z \
    --end 2025-10-09T00:00:00Z \
    --output data/starlink_full.json \
    --min-elev 10.0 \
    --step 30 \
    --progress \
    --track-memory \
    --verbose
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--tle PATH` | TLE file path | (required) |
| `--stations PATH` | Ground stations JSON | (required) |
| `--count N` | Number of satellites | 100 |
| `--start TIME` | Start time (ISO 8601) | (required) |
| `--end TIME` | End time (ISO 8601) | (required) |
| `--output PATH` | Output file | `data/starlink_batch_windows.json` |
| `--min-elev DEG` | Minimum elevation angle | 10.0 |
| `--step SEC` | Time step in seconds | 30 |
| `--checkpoint PATH` | Checkpoint file | `data/checkpoint.json` |
| `--resume` | Resume from checkpoint | false |
| `--progress` | Show progress bars | false |
| `--track-memory` | Track memory usage | false |
| `--verbose, -v` | Verbose logging | false |

## Output Format

### JSON Structure

```json
{
  "meta": {
    "total_windows": 68,
    "station_count": 6,
    "total_satellites": 10,
    "time_range": {
      "start": "2025-10-08T00:00:00Z",
      "end": "2025-10-08T06:00:00Z"
    },
    "generated_at": "2025-10-08T05:04:55Z"
  },
  "stations": [
    "HSINCHU",
    "TAIPEI",
    "KAOHSIUNG",
    "TAICHUNG",
    "TAINAN",
    "HUALIEN"
  ],
  "windows": [
    {
      "satellite": "STARLINK-1008",
      "station": "HSINCHU",
      "start": "2025-10-08T00:15:30Z",
      "end": "2025-10-08T00:25:00Z",
      "duration_sec": 570.0,
      "elevation_max": 45.6
    }
  ]
}
```

### Coverage Statistics

The processor automatically computes:

- **Per-station statistics**:
  - Window count
  - Total duration (seconds)
  - Average duration (seconds)
  - Unique satellites count
  - Time coverage percentage

- **Global statistics**:
  - Total windows across all stations
  - Satellite distribution
  - Processing performance metrics

## Example Output

```
======================================================================
PROCESSING COMPLETE
======================================================================
Output file: data/starlink_test_10sats_6h.json
Duration: 0.72s
Windows generated: 68

Coverage Statistics:
  HSINCHU: 11 windows, 35.5% coverage
  TAIPEI: 12 windows, 41.6% coverage
  KAOHSIUNG: 11 windows, 39.5% coverage
  TAICHUNG: 11 windows, 31.4% coverage
  TAINAN: 11 windows, 39.8% coverage
  HUALIEN: 12 windows, 40.1% coverage
======================================================================
```

## Python API Usage

### Extract Satellites

```python
from pathlib import Path
from starlink_batch_processor import extract_starlink_subset

# Extract first 100 satellites
satellites = extract_starlink_subset(
    Path("data/starlink.tle"),
    count=100
)

print(f"Extracted {len(satellites)} satellites")
print(f"First: {satellites[0]['name']}")
```

### Calculate Windows

```python
from starlink_batch_processor import calculate_batch_windows

stations = [
    {"name": "HSINCHU", "lat": 24.8, "lon": 120.99, "alt": 0.1},
    {"name": "TAIPEI", "lat": 25.03, "lon": 121.56, "alt": 0.05}
]

time_range = {
    'start': '2025-10-08T00:00:00Z',
    'end': '2025-10-08T06:00:00Z'
}

windows = calculate_batch_windows(
    satellites=satellites,
    stations=stations,
    time_range=time_range,
    min_elevation=10.0,
    step_sec=30,
    parallel=True,
    show_progress=True
)

print(f"Found {len(windows)} visibility windows")
```

### Full Pipeline with Processor Class

```python
from pathlib import Path
from starlink_batch_processor import StarlinkBatchProcessor

# Initialize processor
processor = StarlinkBatchProcessor(
    tle_file=Path("data/starlink.tle"),
    stations_file=Path("data/taiwan_ground_stations.json"),
    satellite_count=100,
    output_file=Path("data/output.json")
)

# Run processing
result = processor.run(
    start_time='2025-10-08T00:00:00Z',
    end_time='2025-10-09T00:00:00Z',
    min_elevation=10.0,
    step_sec=30,
    show_progress=True,
    track_memory=True
)

# Check results
if result['status'] == 'success':
    stats = result['statistics']
    perf = result['performance']

    print(f"Windows: {perf['windows_generated']}")
    print(f"Duration: {perf['duration_sec']}s")
    print(f"Memory: {stats['peak_memory_mb']} MB")
```

## Performance Benchmarks

### Test Results (Windows 11, Python 3.13)

| Configuration | Duration | Windows | Memory |
|--------------|----------|---------|--------|
| 10 sats × 6 stations × 6h | 0.72s | 68 | < 100 MB |
| 50 sats × 6 stations × 24h | ~10s | ~800 | < 300 MB |
| 100 sats × 6 stations × 24h | ~20s | ~1600 | < 500 MB |

### Optimization Features

- **Multiprocessing**: Parallel station processing
- **Efficient algorithms**: SGP4 for orbital propagation
- **Memory management**: Streaming window calculation
- **Progress tracking**: tqdm for user feedback

## Checkpoint and Resume

### Save Progress

```bash
python scripts/starlink_batch_processor.py \
    --tle data/starlink.tle \
    --stations data/taiwan_ground_stations.json \
    --count 100 \
    --start 2025-10-08T00:00:00Z \
    --end 2025-10-09T00:00:00Z \
    --checkpoint data/my_checkpoint.json
```

### Resume from Checkpoint

```bash
python scripts/starlink_batch_processor.py \
    --tle data/starlink.tle \
    --stations data/taiwan_ground_stations.json \
    --checkpoint data/my_checkpoint.json \
    --resume
```

## Integration with Existing Tools

### Use with generate_tle_windows.py

The batch processor complements the existing `generate_tle_windows.py`:

```bash
# Old way: Sequential processing
python scripts/generate_tle_windows.py \
    --tle data/starlink.tle \
    --stations data/taiwan_ground_stations.json

# New way: Batch processing with subset
python scripts/starlink_batch_processor.py \
    --tle data/starlink.tle \
    --stations data/taiwan_ground_stations.json \
    --count 100 \
    --start 2025-10-08T00:00:00Z \
    --end 2025-10-09T00:00:00Z
```

### Pipeline Integration

```bash
# Step 1: Extract 100 satellites and calculate windows
python scripts/starlink_batch_processor.py \
    --tle data/starlink.tle \
    --stations data/taiwan_ground_stations.json \
    --count 100 \
    --start 2025-10-08T00:00:00Z \
    --end 2025-10-09T00:00:00Z \
    --output data/starlink_windows.json

# Step 2: Generate NS-3 scenario
python scripts/gen_scenario.py \
    --windows data/starlink_windows.json \
    --output scenarios/starlink_scenario.json

# Step 3: Run simulation
python scripts/run_complex_scenario.py \
    --scenario scenarios/starlink_scenario.json
```

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'sgp4'`
```bash
# Solution:
pip install sgp4
```

**Issue**: `UnicodeEncodeError` on Windows
```bash
# Solution: Set encoding
set PYTHONIOENCODING=utf-8
python scripts/starlink_batch_processor.py ...
```

**Issue**: No windows found
```bash
# Check time range covers satellite passes
# Increase time range or reduce min-elev threshold
python scripts/starlink_batch_processor.py \
    --min-elev 5.0 \
    --start 2025-10-08T00:00:00Z \
    --end 2025-10-09T00:00:00Z
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/test_starlink_batch.py -v

# Run with coverage
pytest tests/test_starlink_batch.py -v --cov=scripts.starlink_batch_processor

# Run specific test class
pytest tests/test_starlink_batch.py::TestStarlinkExtraction -v
```

## Contributing

See the main project README for contribution guidelines.

## License

Same as parent project (TASA SatNet Pipeline).

---

**Documentation Version**: 1.0
**Last Updated**: 2025-10-08
**Maintainer**: TASA SatNet Team
