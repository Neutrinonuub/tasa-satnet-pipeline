# TLE-OASIS Integration Guide

## Overview

The TLE-OASIS integration seamlessly combines satellite visibility windows calculated from Two-Line Element (TLE) sets with windows extracted from OASIS mission planning logs. This enables:

- **Validation**: Cross-verify OASIS-planned windows against orbital mechanics
- **Gap filling**: Add TLE-calculated windows where OASIS data is missing
- **Enrichment**: Enhance OASIS windows with orbital parameters (elevation, azimuth, range)

## Architecture

```
┌─────────────────┐         ┌─────────────────┐
│  OASIS Log      │         │  TLE Files      │
│  (parse_oasis)  │         │  (tle_windows)  │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │         ┌─────────────────┘
         │         │
         ▼         ▼
    ┌────────────────────────┐
    │  tle_oasis_bridge.py   │
    │  - Format conversion   │
    │  - Timezone handling   │
    │  - Merge strategies    │
    │  - Station mapping     │
    └───────────┬────────────┘
                │
                ▼
    ┌────────────────────────┐
    │  Merged Windows JSON   │
    │  - Union / Intersection│
    │  - TLE-only / OASIS    │
    └────────────────────────┘
```

## Quick Start

### Basic Usage

```bash
# Parse OASIS log with TLE integration
python scripts/parse_oasis_log.py \
    data/sample_oasis.log \
    --tle-file data/iss.tle \
    --stations data/taiwan_ground_stations.json \
    --merge-strategy union \
    --output data/merged_windows.json
```

### Merge Strategies

1. **Union** (default): All windows from both sources, deduplicated
   ```bash
   --merge-strategy union
   ```

2. **Intersection**: Only overlapping windows (verified by both sources)
   ```bash
   --merge-strategy intersection
   ```

3. **TLE-only**: Use only TLE-calculated windows
   ```bash
   --merge-strategy tle-only
   ```

4. **OASIS-only**: Use only OASIS log windows (ignore TLE)
   ```bash
   --merge-strategy oasis-only
   ```

## Integration Module (tle_oasis_bridge.py)

### Core Functions

#### 1. Format Conversion

```python
from tle_oasis_bridge import convert_tle_to_oasis_format, load_ground_stations

# Load ground stations
stations = load_ground_stations(Path("data/taiwan_ground_stations.json"))

# Convert TLE windows to OASIS format
tle_windows = [
    {
        "type": "tle_pass",
        "start": "2025-10-08T10:00:00Z",
        "end": "2025-10-08T10:15:00Z",
        "sat": "ISS",
        "gw": "24.788,120.998"  # Coordinates
    }
]

oasis_windows = convert_tle_to_oasis_format(tle_windows, stations=stations)
# Result:
# [{
#     "type": "tle",
#     "start": "2025-10-08T10:00:00Z",
#     "end": "2025-10-08T10:15:00Z",
#     "sat": "ISS",
#     "gw": "HSINCHU",  # Mapped to station name
#     "source": "tle"
# }]
```

#### 2. Window Merging

```python
from tle_oasis_bridge import merge_windows

oasis_windows = [
    {
        "type": "cmd",
        "start": "2025-10-08T10:05:00Z",
        "end": "2025-10-08T10:20:00Z",
        "sat": "ISS",
        "gw": "HSINCHU",
        "source": "log"
    }
]

tle_windows = [
    {
        "type": "tle_pass",
        "start": "2025-10-08T10:00:00Z",
        "end": "2025-10-08T10:15:00Z",
        "sat": "ISS",
        "gw": "24.788,120.998"
    }
]

# Merge with union strategy
merged = merge_windows(
    oasis_windows,
    tle_windows,
    strategy='union',
    stations=stations
)
# Result: Single merged window from 10:00-10:20 (union of both)
```

#### 3. Timezone Handling

```python
from tle_oasis_bridge import normalize_timestamp, convert_timestamp_timezone

# Normalize to UTC
utc_time = normalize_timestamp("2025-10-08T18:15:30+08:00", "UTC")
# Result: "2025-10-08T10:15:30Z"

# Convert between timezones (requires pytz)
taiwan_time = convert_timestamp_timezone(
    "2025-10-08T10:15:30Z",
    from_tz="UTC",
    to_tz="Asia/Taipei"
)
```

## Use Cases

### Use Case 1: Validate OASIS Windows

**Scenario**: Verify that OASIS-planned communication windows align with satellite visibility.

```bash
# Parse OASIS log and cross-check with TLE
python scripts/parse_oasis_log.py \
    data/mission_plan.log \
    --tle-file data/satellite.tle \
    --stations data/taiwan_ground_stations.json \
    --merge-strategy intersection \
    --output data/validated_windows.json
```

**Result**: Only windows confirmed by both OASIS and TLE calculations.

### Use Case 2: Fill Missing Windows

**Scenario**: OASIS log is incomplete; fill gaps with TLE-calculated windows.

```bash
# Add TLE windows where OASIS data is missing
python scripts/parse_oasis_log.py \
    data/partial_oasis.log \
    --tle-file data/satellite.tle \
    --stations data/taiwan_ground_stations.json \
    --merge-strategy union \
    --output data/complete_windows.json
```

**Result**: Comprehensive window list combining OASIS and TLE sources.

### Use Case 3: TLE-Only Mode

**Scenario**: No OASIS log available; generate windows from TLE.

```bash
# Create empty OASIS log (or use minimal log)
touch data/empty.log

# Generate windows from TLE only
python scripts/parse_oasis_log.py \
    data/empty.log \
    --tle-file data/satellite.tle \
    --stations data/taiwan_ground_stations.json \
    --merge-strategy tle-only \
    --output data/tle_windows.json
```

### Use Case 4: Multi-Station Coverage

**Scenario**: Calculate visibility windows for all Taiwan ground stations.

```bash
# Automatic: parse_oasis_log.py will calculate for ALL stations in JSON
python scripts/parse_oasis_log.py \
    data/oasis.log \
    --tle-file data/satellite.tle \
    --stations data/taiwan_ground_stations.json \
    --merge-strategy union \
    --output data/multi_station_windows.json
```

## Advanced Features

### Station Coordinate Mapping

The bridge automatically maps TLE gateway coordinates to station names:

```python
from tle_oasis_bridge import find_station_by_coords

stations = [
    {"name": "HSINCHU", "lat": 24.7881, "lon": 120.9979, "alt": 52},
    {"name": "TAIPEI", "lat": 25.0330, "lon": 121.5654, "alt": 10}
]

# Find station near coordinates (within 0.1 degree tolerance)
name = find_station_by_coords(24.788, 120.998, stations, tolerance=0.1)
# Result: "HSINCHU"
```

### Overlap Detection

```python
from tle_oasis_bridge import windows_overlap

w1 = {
    'start': '2025-10-08T10:00:00Z',
    'end': '2025-10-08T10:20:00Z'
}
w2 = {
    'start': '2025-10-08T10:15:00Z',
    'end': '2025-10-08T10:30:00Z'
}

overlaps = windows_overlap(w1, w2)  # True
```

### Custom Merge Logic

```python
from tle_oasis_bridge import merge_overlapping_windows

w1 = {
    'type': 'tle',
    'start': '2025-10-08T10:00:00Z',
    'end': '2025-10-08T10:20:00Z',
    'sat': 'ISS',
    'gw': 'HSINCHU',
    'source': 'tle'
}
w2 = {
    'type': 'cmd',
    'start': '2025-10-08T10:15:00Z',
    'end': '2025-10-08T10:30:00Z',
    'sat': 'ISS',
    'gw': 'HSINCHU',
    'source': 'log'
}

merged = merge_overlapping_windows(w1, w2)
# Result: {
#     'start': '2025-10-08T10:00:00Z',  # Earliest start
#     'end': '2025-10-08T10:30:00Z',    # Latest end
#     'type': 'cmd',                     # Prefer log metadata
#     'source': 'log'
# }
```

## Testing

### Run Integration Tests

```bash
# All integration tests
pytest tests/test_tle_oasis_integration.py -v

# Specific test category
pytest tests/test_tle_oasis_integration.py::test_merge_windows_union -v
pytest tests/test_tle_oasis_integration.py::test_convert_tle_to_oasis_format -v

# Coverage report
pytest tests/test_tle_oasis_integration.py --cov=scripts.tle_oasis_bridge
```

### Test Coverage

The integration test suite includes:

- ✅ 10+ timezone handling tests
- ✅ 8+ format conversion tests
- ✅ 12+ merge strategy tests
- ✅ 6+ ground station mapping tests
- ✅ 4+ end-to-end integration tests
- ✅ 5+ edge case tests
- ✅ 2+ performance tests

Expected coverage: **95%+**

## Configuration

### Ground Stations JSON Format

```json
{
  "ground_stations": [
    {
      "name": "HSINCHU",
      "location": "新竹站",
      "lat": 24.7881,
      "lon": 120.9979,
      "alt": 52,
      "type": "command_control",
      "capacity_beams": 8,
      "frequency_bands": ["S-band", "X-band", "Ka-band"]
    }
  ],
  "network_info": {
    "operator": "TASA",
    "country": "Taiwan",
    "total_stations": 6
  }
}
```

### TLE File Format

Standard two-line or three-line format:

```
ISS (ZARYA)
1 25544U 98067A   25280.50000000  .00002182  00000-0  41420-4 0  9990
2 25544  51.6400 208.9163 0002571  59.2676 120.7846 15.54225995999999
```

Or without name line:

```
1 25544U 98067A   25280.50000000  .00002182  00000-0  41420-4 0  9990
2 25544  51.6400 208.9163 0002571  59.2676 120.7846 15.54225995999999
```

## Output Format

### Merged Windows JSON

```json
{
  "meta": {
    "source": "data/sample_oasis.log",
    "count": 5,
    "tle_file": "data/iss.tle",
    "merge_strategy": "union"
  },
  "windows": [
    {
      "type": "cmd",
      "start": "2025-10-08T10:00:00Z",
      "end": "2025-10-08T10:20:00Z",
      "sat": "ISS",
      "gw": "HSINCHU",
      "source": "log"
    },
    {
      "type": "tle",
      "start": "2025-10-08T12:00:00Z",
      "end": "2025-10-08T12:12:00Z",
      "sat": "ISS",
      "gw": "TAIPEI",
      "source": "tle",
      "elevation_deg": 45.2,
      "azimuth_deg": 180.5,
      "range_km": 1234.56
    }
  ]
}
```

### Window Types

- `cmd`: Command/control window (from OASIS log pairing)
- `xband`: X-band data link window (explicit from OASIS log)
- `tle`: TLE-derived visibility window
- Source field:
  - `log`: From OASIS log parsing
  - `tle`: From TLE calculation
  - `log+tle`: Intersection (verified by both)

## Performance

### Benchmarks

| Operation | Windows | Time |
|-----------|---------|------|
| Format conversion | 100 | < 10ms |
| Union merge | 100 + 100 | < 100ms |
| Intersection merge | 100 + 100 | < 150ms |
| TLE calculation | 1 sat × 6 stations × 24h | ~2-4s |

### Optimization Tips

1. **Batch processing**: Calculate TLE windows for all stations in one pass
2. **Time range**: Limit TLE calculations to OASIS window time range
3. **Step size**: Use larger `--tle-step` (60s) for faster calculation
4. **Caching**: Reuse TLE window calculations across runs

## Troubleshooting

### TLE Calculation Fails

**Symptom**: "TLE calculation failed" warning

**Solutions**:
- Check TLE file format (must be valid two-line or three-line format)
- Verify time range is reasonable (not too far in past/future)
- Ensure stations JSON has valid lat/lon coordinates
- Check that numpy and sgp4 packages are installed

### Station Mapping Not Working

**Symptom**: TLE windows show coordinates instead of station names

**Solutions**:
- Verify `--stations` path is correct
- Check stations JSON format matches specification
- Ensure coordinates match within tolerance (default 0.1°)
- Use larger tolerance: modify `find_station_by_coords()` tolerance parameter

### Merge Strategy Produces Empty Results

**Symptom**: Intersection strategy returns 0 windows

**Solutions**:
- Check that satellite names match between OASIS and TLE
- Verify gateway names are consistent
- Ensure time windows actually overlap
- Try `union` strategy to see all windows first

## API Reference

See inline documentation in `scripts/tle_oasis_bridge.py` for detailed API reference.

Key functions:
- `convert_tle_to_oasis_format()`: Format conversion
- `merge_windows()`: Main merge function
- `normalize_timestamp()`: Timezone normalization
- `find_station_by_coords()`: Coordinate to name mapping
- `windows_overlap()`: Overlap detection
- `merge_overlapping_windows()`: Window merging

## Integration with Pipeline

The TLE-OASIS integration fits into the full pipeline:

```
OASIS Log + TLE → parse_oasis_log.py (with --tle-file)
                ↓
           Merged Windows JSON
                ↓
           gen_scenario.py
                ↓
           NS-3/SNS3 Scenario
                ↓
           metrics.py + scheduler.py
                ↓
           KPI Reports
```

## Future Enhancements

Planned features:
- [ ] Multi-TLE file support (constellation processing)
- [ ] Doppler shift calculation
- [ ] Link budget estimation
- [ ] Weather impact modeling
- [ ] Real-time TLE updates from Celestrak
- [ ] Propagation model integration

---

**Last Updated**: 2025-10-08
**Version**: 1.0.0
**Author**: TASA SatNet Pipeline Team
