# TLE-OASIS Integration Architecture

## System Overview

The TLE-OASIS integration provides a seamless bridge between satellite orbital mechanics (TLE) and mission planning (OASIS), enabling validation, gap-filling, and enrichment of satellite communication windows.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     TLE-OASIS Integration System                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Input Layer                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │  OASIS Log   │    │  TLE Files   │    │  Ground Stations│  │
│  │  .log        │    │  .tle        │    │  .json          │  │
│  └──────┬───────┘    └──────┬───────┘    └────────┬────────┘  │
│         │                   │                      │           │
└─────────┼───────────────────┼──────────────────────┼───────────┘
          │                   │                      │
          │                   │                      │
┌─────────┼───────────────────┼──────────────────────┼───────────┐
│  Processing Layer           │                      │           │
├─────────┼───────────────────┼──────────────────────┼───────────┤
│         ▼                   ▼                      ▼           │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │parse_oasis   │    │tle_windows   │    │Station Config   │  │
│  │_log.py       │    │.py            │    │Loader           │  │
│  │              │    │              │    │                 │  │
│  │- Parse enter │    │- SGP4 prop   │    │- Load stations  │  │
│  │- Parse exit  │    │- Elevation   │    │- Coord mapping  │  │
│  │- Parse xband │    │- Azimuth     │    │- Validation     │  │
│  │- Pair windows│    │- Range calc  │    │                 │  │
│  └──────┬───────┘    └──────┬───────┘    └────────┬────────┘  │
│         │                   │                      │           │
│         └───────────────────┴──────────────────────┘           │
│                             │                                  │
│                             ▼                                  │
│                  ┌─────────────────────┐                       │
│                  │ tle_oasis_bridge.py │                       │
│                  │                     │                       │
│                  │ Core Functions:     │                       │
│                  │ ├─ Format Convert   │                       │
│                  │ ├─ Timezone Handle  │                       │
│                  │ ├─ Overlap Detect   │                       │
│                  │ ├─ Window Merge     │                       │
│                  │ └─ Station Map      │                       │
│                  └──────────┬──────────┘                       │
│                             │                                  │
└─────────────────────────────┼──────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Output Layer                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Merged Windows JSON                                    │   │
│  │                                                         │   │
│  │  {                                                      │   │
│  │    "meta": {                                            │   │
│  │      "source": "oasis.log",                             │   │
│  │      "tle_file": "satellite.tle",                       │   │
│  │      "merge_strategy": "union",                         │   │
│  │      "count": 15                                        │   │
│  │    },                                                   │   │
│  │    "windows": [                                         │   │
│  │      {                                                  │   │
│  │        "type": "cmd",                                   │   │
│  │        "start": "2025-10-08T10:00:00Z",                 │   │
│  │        "end": "2025-10-08T10:20:00Z",                   │   │
│  │        "sat": "ISS",                                    │   │
│  │        "gw": "HSINCHU",                                 │   │
│  │        "source": "log"                                  │   │
│  │      },                                                 │   │
│  │      ...                                                │   │
│  │    ]                                                    │   │
│  │  }                                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                  │
└─────────────────────────────┼──────────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  Downstream       │
                    │  - gen_scenario   │
                    │  - metrics        │
                    │  - scheduler      │
                    └───────────────────┘
```

---

## Module Details

### 1. Core Bridge Module (`tle_oasis_bridge.py`)

**Responsibilities**:
- Format conversion between TLE and OASIS window formats
- Timezone normalization and handling
- Ground station coordinate to name mapping
- Window overlap detection and merging
- Implementation of merge strategies

**Key Components**:

```python
# Timezone Handling
normalize_timestamp(ts: str, target_tz: str) -> str
convert_timestamp_timezone(ts: str, from_tz: str, to_tz: str) -> str

# Ground Station Mapping
load_ground_stations(file: Path) -> List[Dict]
find_station_by_coords(lat: float, lon: float, stations: List) -> str
parse_tle_gateway_coords(gw_str: str) -> Tuple[float, float]

# Format Conversion
convert_tle_to_oasis_format(
    tle_windows: List[Dict],
    stations: Optional[List[Dict]],
    window_type: str
) -> List[Dict]

# Merging Logic
windows_overlap(w1: Dict, w2: Dict) -> bool
merge_overlapping_windows(w1: Dict, w2: Dict) -> Dict
merge_union(oasis: List, tle: List) -> List
merge_intersection(oasis: List, tle: List) -> List

# Main Interface
merge_windows(
    oasis_windows: List[Dict],
    tle_windows: List[Dict],
    strategy: MergeStrategy,
    stations: Optional[List[Dict]]
) -> List[Dict]
```

**Data Flow**:
```
TLE Windows (raw)
    ↓
[normalize_timestamp]
    ↓
[parse_tle_gateway_coords]
    ↓
[find_station_by_coords]
    ↓
[convert_tle_to_oasis_format]
    ↓
TLE Windows (OASIS format)
    ↓
[merge_windows]
    ↓
Merged Windows
```

---

### 2. Extended Parser (`parse_oasis_log.py`)

**Integration Points**:

```python
# New CLI Arguments
--tle-file PATH              # TLE file for integration
--stations PATH              # Ground stations JSON
--merge-strategy STRATEGY    # union/intersection/tle-only/oasis-only
--min-elevation FLOAT        # Min elevation for TLE windows (°)
--tle-step INT              # TLE calculation time step (s)

# Integration Flow
1. Parse OASIS log normally
2. If --tle-file provided:
   a. Load ground stations
   b. Determine time range from OASIS windows
   c. Calculate TLE windows for all stations
   d. Merge using specified strategy
3. Output merged results
```

**Code Structure**:
```python
def main():
    # ... existing OASIS parsing ...

    # TLE Integration (lines 218-297)
    if args.tle_file:
        from tle_oasis_bridge import merge_windows, load_ground_stations

        # Load stations
        stations = load_ground_stations(args.stations)

        # Calculate TLE windows
        tle_windows_all = []
        for station in stations:
            # Run tle_windows.py for each station
            subprocess.run([...])
            tle_windows_all.extend(result)

        # Merge
        final = merge_windows(
            oasis_windows=final,
            tle_windows=tle_windows_all,
            strategy=args.merge_strategy,
            stations=stations
        )

    # ... output results ...
```

---

### 3. TLE Window Calculator (`tle_windows.py`)

**Existing Module** - No modifications needed

**Responsibilities**:
- Parse TLE files (2-line or 3-line format)
- Propagate satellite position using SGP4
- Calculate elevation, azimuth, range from ground station
- Detect visibility windows (elevation > min threshold)

**Usage by Bridge**:
```bash
python scripts/tle_windows.py \
    --tle satellite.tle \
    --lat 24.7881 --lon 120.9979 --alt 52 \
    --start 2025-10-08T00:00:00Z \
    --end 2025-10-09T00:00:00Z \
    --min-elev 10.0 \
    --step 30 \
    --out windows.json
```

---

## Data Models

### OASIS Window Format

```json
{
  "type": "cmd|xband|tle",
  "start": "2025-10-08T10:00:00Z",
  "end": "2025-10-08T10:20:00Z",
  "sat": "ISS",
  "gw": "HSINCHU",
  "source": "log|tle|log+tle",
  "elevation_deg": 45.2,      // Optional
  "azimuth_deg": 180.5,       // Optional
  "range_km": 1234.56         // Optional
}
```

### TLE Window Format (Input)

```json
{
  "type": "tle_pass",
  "start": "2025-10-08T10:00:00Z",
  "end": "2025-10-08T10:15:00Z",
  "sat": "ISS",
  "gw": "24.788,120.998"      // Coordinates
}
```

### Ground Station Config

```json
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
```

---

## Merge Strategies

### 1. Union Strategy

**Algorithm**:
```
FOR each TLE window:
    IF overlaps with any OASIS window (same sat/gw):
        Merge windows (take union of time periods)
    ELSE:
        Add TLE window to results
RETURN all OASIS windows + merged/new TLE windows
```

**Use Case**: Fill gaps in OASIS planning

**Example**:
```
OASIS:   |----------|                  (10:00-10:20)
TLE:          |-----------|             (10:10-10:30)
Result:  |----------------|             (10:00-10:30, merged)

OASIS:   |----------|                  (10:00-10:20)
TLE:                      |--------|    (14:00-14:10)
Result:  |----------|     |--------|    (both kept)
```

---

### 2. Intersection Strategy

**Algorithm**:
```
FOR each OASIS window:
    FOR each TLE window:
        IF overlaps AND same sat/gw:
            Create intersection window (overlap period only)
            Mark as "log+tle" (verified by both)
RETURN only intersection windows
```

**Use Case**: Validate OASIS planning against orbital mechanics

**Example**:
```
OASIS:   |----------|                  (10:00-10:20)
TLE:          |-----------|             (10:10-10:30)
Result:       |------|                  (10:10-10:20, intersection)
```

---

### 3. TLE-Only Strategy

**Algorithm**:
```
Convert all TLE windows to OASIS format
RETURN TLE windows only
```

**Use Case**: No OASIS data available

---

### 4. OASIS-Only Strategy

**Algorithm**:
```
RETURN OASIS windows only (ignore TLE)
```

**Use Case**: Debugging, TLE data unreliable

---

## Processing Pipeline

### Full Integration Pipeline

```
1. Input Validation
   ├─ Validate OASIS log file
   ├─ Validate TLE file format
   └─ Validate ground stations JSON

2. OASIS Parsing
   ├─ Extract enter/exit command windows
   ├─ Extract X-band data link windows
   ├─ Pair enter/exit events (O(n) algorithm)
   └─ Filter by satellite, gateway, duration

3. TLE Processing (if --tle-file provided)
   ├─ Load ground stations configuration
   ├─ Determine time range from OASIS windows
   ├─ FOR each ground station:
   │   ├─ Run tle_windows.py
   │   ├─ Calculate visibility windows
   │   └─ Collect TLE windows
   └─ Aggregate all TLE windows

4. Format Conversion
   ├─ Convert TLE windows to OASIS format
   ├─ Normalize timestamps to UTC
   ├─ Map coordinates to station names
   └─ Preserve optional fields (elevation, azimuth, range)

5. Window Merging
   ├─ Select merge strategy
   ├─ Detect overlapping windows
   ├─ Merge or filter based on strategy
   └─ Validate merged windows

6. Output Generation
   ├─ Construct output JSON
   ├─ Add metadata (source, strategy, count)
   ├─ Schema validation
   └─ Write to file
```

---

## Error Handling

### Error Categories

1. **Input Errors**
   - Missing OASIS log file
   - Invalid TLE file format
   - Missing ground stations JSON
   - Malformed JSON

2. **Processing Errors**
   - TLE calculation failure (SGP4 errors)
   - Station coordinate mapping failure
   - Timestamp parsing errors
   - Overlap detection edge cases

3. **Output Errors**
   - Schema validation failure
   - File write permission errors

### Error Recovery

```python
try:
    # TLE integration
    from tle_oasis_bridge import merge_windows
    stations = load_ground_stations(args.stations)
    tle_windows = calculate_tle_windows(...)
    final = merge_windows(oasis, tle_windows, strategy, stations)
except ImportError:
    # Missing dependency
    print("WARNING: TLE integration unavailable, continuing with OASIS-only")
    final = oasis_windows
except Exception as e:
    # Any other error
    print(f"WARNING: TLE integration failed: {e}")
    print("Continuing with OASIS-only windows...")
    final = oasis_windows
```

**Philosophy**: Graceful degradation - always output OASIS windows even if TLE integration fails

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| OASIS parsing | O(n) | Single pass through log |
| TLE calculation | O(m·s·t) | m stations, s steps, t satellites |
| Format conversion | O(k) | k TLE windows |
| Overlap detection | O(n·k) | n OASIS, k TLE windows |
| Union merge | O(n·k) | Worst case: all overlap checks |
| Intersection merge | O(n·k) | Same as union |

### Space Complexity

| Component | Space | Notes |
|-----------|-------|-------|
| OASIS windows | O(n) | n parsed windows |
| TLE windows | O(k) | k calculated windows |
| Merged output | O(n+k) | Worst case: union of all |
| Temporary | O(1) | Minimal overhead |

### Performance Benchmarks

| Dataset | OASIS | TLE | Merge Time | Total Time |
|---------|-------|-----|------------|------------|
| Small | 10 | 10 | <10ms | ~2s |
| Medium | 100 | 100 | <100ms | ~10s |
| Large | 1000 | 1000 | <1s | ~60s |

**Bottleneck**: TLE calculation (SGP4 propagation), not merging

---

## Testing Strategy

### Test Pyramid

```
                    ▲
                   / \
                  /   \
                 /  E2E \        1 test
                /_______\
               /         \
              / Integration \    31 tests
             /___________  _\
            /               \
           /  Unit Tests     \  (covered by integration)
          /___________________\
```

### Test Coverage

**Integration Tests** (31 tests):
- Timezone handling (3)
- Station mapping (4)
- Format conversion (3)
- Overlap detection (4)
- Window merging (6)
- Merge strategies (5)
- End-to-end (1)
- Edge cases (3)
- Performance (1)
- Error handling (1)

**Coverage Metrics**:
- `tle_oasis_bridge.py`: 72%
- `parse_oasis_log.py` (TLE section): 73%
- `tle_windows.py`: 98%

---

## Deployment

### Dependencies

```python
# Core dependencies
numpy>=1.20.0
sgp4>=2.20
jsonschema>=4.0.0

# Optional dependencies
pytz>=2021.3  # For non-UTC timezone support
```

### Integration Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Ground Stations**
   - Edit `data/taiwan_ground_stations.json`
   - Add/modify station configurations

3. **Obtain TLE Data**
   - Download from Celestrak/Space-Track
   - Place in `data/` directory

4. **Run Integration**
   ```bash
   python scripts/parse_oasis_log.py \
       data/oasis.log \
       --tle-file data/satellite.tle \
       --stations data/taiwan_ground_stations.json \
       --merge-strategy union \
       -o data/merged.json
   ```

---

## Future Architecture Enhancements

### Planned Improvements

1. **Caching Layer**
   ```
   TLE Calculation → Cache → Bridge Module
                      ↓
                   Disk/Redis
   ```
   Benefit: Avoid recalculating TLE windows for same parameters

2. **Parallel Processing**
   ```
   TLE Calculation (Station 1) ┐
   TLE Calculation (Station 2) ├→ Merge → Output
   TLE Calculation (Station 3) ┘
   ```
   Benefit: 3-6x speedup for multi-station scenarios

3. **Real-time TLE Updates**
   ```
   Celestrak API → TLE Update Service → Bridge Module
   ```
   Benefit: Always use latest orbital elements

4. **Propagation Model Integration**
   ```
   Bridge Module → Propagation Model → Link Budget
                                    ↓
                                Feasibility Check
   ```
   Benefit: Account for atmospheric effects, signal strength

---

## Conclusion

The TLE-OASIS integration architecture provides:

✅ **Modularity**: Clear separation of concerns
✅ **Extensibility**: Easy to add new merge strategies
✅ **Robustness**: Graceful error handling
✅ **Performance**: Optimized algorithms (O(n) where possible)
✅ **Testability**: Comprehensive test coverage
✅ **Usability**: Simple CLI and programmatic API

**Status**: Production Ready ✅

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-08
**Maintainer**: TASA SatNet Pipeline Team
