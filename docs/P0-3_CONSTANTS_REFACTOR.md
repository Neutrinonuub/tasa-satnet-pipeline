# P0-3: Constants Configuration Refactor

## Summary

Successfully replaced all magic numbers in the codebase with named constants from a centralized configuration module.

## Changes Made

### 1. Created `config/constants.py`

A comprehensive constants module with the following classes:

#### PhysicalConstants
- `SPEED_OF_LIGHT_KM_S = 299_792.458` - Speed of light in km/s
- `DEFAULT_ALTITUDE_KM = 550` - Default LEO satellite altitude

#### LatencyConstants
- `TRANSPARENT_PROCESSING_MS = 5.0` - Transparent mode processing delay
- `REGENERATIVE_PROCESSING_MS = 10.0` - Regenerative mode processing delay
- `MIN_QUEUING_DELAY_MS = 0.5` - Low traffic queuing delay
- `MEDIUM_QUEUING_DELAY_MS = 2.0` - Medium traffic queuing delay
- `MAX_QUEUING_DELAY_MS = 5.0` - High traffic queuing delay
- `LOW_TRAFFIC_THRESHOLD_SEC = 60` - Low traffic threshold
- `MEDIUM_TRAFFIC_THRESHOLD_SEC = 300` - Medium traffic threshold

#### NetworkConstants
- `PACKET_SIZE_BYTES = 1500` - MTU packet size
- `PACKET_SIZE_KB = 1.5` - Packet size in KB
- `DEFAULT_BANDWIDTH_MBPS = 100` - Default gateway bandwidth
- `DEFAULT_LINK_BANDWIDTH_MBPS = 50` - Default link bandwidth
- `DEFAULT_UTILIZATION_PERCENT = 80.0` - Default link utilization
- `DEFAULT_BUFFER_SIZE_MB = 10` - Default buffer size

#### ValidationConstants
- `MAX_FILE_SIZE_MB = 100` - Maximum file size
- `MAX_FILE_SIZE_BYTES = 104_857_600` - Maximum file size in bytes
- `DEFAULT_SIMULATION_DURATION_SEC = 86400` - 24-hour simulation

#### PercentileConstants
- `P95 = 95` - 95th percentile
- `P99 = 99` - 99th percentile

### 2. Updated `scripts/gen_scenario.py`

Replaced magic numbers with constants:
- Line 69: `altitude_km: 550` → `PhysicalConstants.DEFAULT_ALTITUDE_KM`
- Line 79: `capacity_mbps: 100` → `NetworkConstants.DEFAULT_BANDWIDTH_MBPS`
- Line 92: `bandwidth_mbps: 50` → `NetworkConstants.DEFAULT_LINK_BANDWIDTH_MBPS`
- Line 132: `return 5.0` → `LatencyConstants.TRANSPARENT_PROCESSING_MS`
- Line 134: `return 10.0` → `LatencyConstants.REGENERATIVE_PROCESSING_MS`
- Line 141: `data_rate_mbps: 50` → `NetworkConstants.DEFAULT_LINK_BANDWIDTH_MBPS`
- Line 142: `simulation_duration_sec: 86400` → `ValidationConstants.DEFAULT_SIMULATION_DURATION_SEC`
- Line 143: `processing_delay_ms: 5.0` → `LatencyConstants.TRANSPARENT_PROCESSING_MS`
- Line 145: `buffer_size_mb: 10` → `NetworkConstants.DEFAULT_BUFFER_SIZE_MB`

### 3. Updated `scripts/metrics.py`

Replaced magic numbers and class constant with centralized constants:
- Removed: `SPEED_OF_LIGHT = 299792.458` class constant
- Line 86: Default data rate now uses `NetworkConstants.DEFAULT_LINK_BANDWIDTH_MBPS`
- Line 115: `altitude_km = 550` → `PhysicalConstants.DEFAULT_ALTITUDE_KM`
- Line 118: `self.SPEED_OF_LIGHT` → `PhysicalConstants.SPEED_OF_LIGHT_KM_S`
- Line 124-129: Queuing delay thresholds use `LatencyConstants.*`
- Line 133: `packet_size_kb = 1.5` → `NetworkConstants.PACKET_SIZE_KB`
- Line 134: Default data rate uses `NetworkConstants.DEFAULT_LINK_BANDWIDTH_MBPS`
- Line 141: `0.8` → `NetworkConstants.DEFAULT_UTILIZATION_PERCENT / 100.0`
- Line 158: `95` → `PercentileConstants.P95`

### 4. Created `tests/test_constants.py`

Comprehensive test suite with 17 tests covering:
- Physical constants validation
- Latency constants validation
- Network constants validation
- Validation constants checks
- Percentile constants verification
- Integration tests verifying constants are used correctly in modules
- Backward compatibility tests

## Test Results

All 17 tests pass successfully:
```
tests/test_constants.py::TestPhysicalConstants::test_speed_of_light_value PASSED
tests/test_constants.py::TestPhysicalConstants::test_default_altitude PASSED
tests/test_constants.py::TestLatencyConstants::test_processing_delays PASSED
tests/test_constants.py::TestLatencyConstants::test_regenerative_greater_than_transparent PASSED
tests/test_constants.py::TestLatencyConstants::test_queuing_delays PASSED
tests/test_constants.py::TestLatencyConstants::test_traffic_thresholds PASSED
tests/test_constants.py::TestNetworkConstants::test_packet_size PASSED
tests/test_constants.py::TestNetworkConstants::test_bandwidth_constants PASSED
tests/test_constants.py::TestNetworkConstants::test_utilization PASSED
tests/test_constants.py::TestNetworkConstants::test_buffer_size PASSED
tests/test_constants.py::TestValidationConstants::test_file_size_limits PASSED
tests/test_constants.py::TestValidationConstants::test_simulation_duration PASSED
tests/test_constants.py::TestPercentileConstants::test_percentile_values PASSED
tests/test_constants.py::TestConstantsUsage::test_no_magic_numbers_in_gen_scenario PASSED
tests/test_constants.py::TestConstantsUsage::test_constants_used_in_metrics PASSED
tests/test_constants.py::TestConstantsUsage::test_parameters_generation PASSED
tests/test_constants.py::TestBackwardCompatibility::test_convenience_exports PASSED

17 passed in 1.55s
```

## Benefits

1. **Maintainability**: All configuration values are in one place
2. **Readability**: Named constants make code self-documenting
3. **Type Safety**: Constants are properly typed
4. **Testability**: Easy to verify values and usage
5. **Consistency**: Same values used throughout codebase
6. **Flexibility**: Easy to adjust parameters for different scenarios

## Usage Example

```python
from config.constants import LatencyConstants, NetworkConstants

# Use named constants instead of magic numbers
processing_delay = LatencyConstants.TRANSPARENT_PROCESSING_MS  # 5.0 ms
bandwidth = NetworkConstants.DEFAULT_LINK_BANDWIDTH_MBPS  # 50 Mbps
```

## Files Created

- `config/constants.py` - Main constants module (135 lines)
- `config/__init__.py` - Module exports (22 lines)
- `tests/test_constants.py` - Comprehensive test suite (217 lines)
- `docs/P0-3_CONSTANTS_REFACTOR.md` - This documentation

## Files Modified

- `scripts/gen_scenario.py` - 11 replacements
- `scripts/metrics.py` - 10 replacements

## Verification

Both updated scripts still work correctly:
```bash
python scripts/gen_scenario.py --help  # ✓ Works
python scripts/metrics.py --help       # ✓ Works
pytest tests/test_constants.py -v     # ✓ 17/17 passed
```

## Next Steps

Future developers should:
1. Always use constants from `config.constants` instead of hardcoded values
2. Add new constants to appropriate class in `config/constants.py`
3. Update tests when adding new constants
4. Import constants at module level for better readability

## Compliance

This refactor fulfills **P0-3** requirements:
- ✅ Created `config/constants.py` with all required constant classes
- ✅ Updated `scripts/gen_scenario.py` to use constants
- ✅ Updated `scripts/metrics.py` to use constants
- ✅ Created comprehensive test suite in `tests/test_constants.py`
- ✅ All tests pass (17/17)
- ✅ No magic numbers remain in target files
