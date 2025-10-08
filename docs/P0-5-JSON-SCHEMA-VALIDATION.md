# P0-5: JSON Schema Validation Implementation

## Overview

Comprehensive JSON Schema validation has been implemented across the entire TASA SatNet Pipeline to ensure data integrity and early error detection.

## Implementation Summary

### 1. Schema Definitions (`config/schemas.py`)

**Three comprehensive schemas created:**

1. **OASIS_WINDOW_SCHEMA** - Validates parsed satellite communication windows
   - Window types: `cmd`, `xband`, `cmd_enter`, `cmd_exit`, `tle`
   - Time format: ISO 8601 (UTC or timezone offset)
   - Required fields: `type`, `sat`, `gw`, `source`
   - Optional fields: `elevation_deg`, `azimuth_deg`, `range_km`

2. **SCENARIO_SCHEMA** - Validates NS-3/SNS3 scenario configurations
   - Metadata: name, mode (transparent/regenerative), timestamps
   - Topology: satellites, gateways, links with proper constraints
   - Events: link_up, link_down, handover, failure, recovery
   - Parameters: relay mode, propagation model, data rates, delays

3. **METRICS_SCHEMA** - Validates performance metrics output
   - Session statistics
   - Latency breakdown: mean, min, max, p95
   - Throughput metrics: mean, min, max
   - Mode validation

### 2. Validation Functions

**Core validators:**
```python
validate_windows(data: Dict) -> None
validate_scenario(data: Dict) -> None
validate_metrics(data: Dict) -> None
validate_window_item(window: Dict) -> None
```

**Custom exception:**
```python
class ValidationError(Exception):
    """Provides detailed validation error messages with path information"""
```

### 3. Integration into Pipeline

**parse_oasis_log.py:**
- Validates each parsed window before adding to results
- Validates complete output before saving
- Provides `--skip-validation` flag for edge cases
- Returns non-zero exit code on validation failure

**gen_scenario.py:**
- Validates input windows data
- Validates generated scenario before output
- Provides detailed error messages
- Supports `--skip-validation` flag

**metrics.py:**
- Validates input scenario configuration
- Validates generated metrics summary
- Ensures data consistency throughout calculation
- Returns errors with clear diagnostics

### 4. Test Coverage (`tests/test_schemas.py`)

**22 comprehensive tests covering:**

**Windows Schema (8 tests):**
- ✓ Valid window data passes
- ✓ Invalid window type rejected
- ✓ Missing required fields detected
- ✓ ISO 8601 time format validated
- ✓ Window type enum validated
- ✓ Optional elevation fields accepted
- ✓ Elevation range enforced (0-90°)
- ✓ Negative count rejected

**Scenario Schema (6 tests):**
- ✓ Valid scenario passes
- ✓ Invalid relay mode rejected
- ✓ Missing topology detected
- ✓ Empty satellites array rejected
- ✓ Altitude constraints enforced (160-50000 km)
- ✓ Zero data rate rejected (exclusiveMinimum)

**Metrics Schema (5 tests):**
- ✓ Valid metrics pass
- ✓ Missing latency field detected
- ✓ Negative values rejected
- ✓ Invalid mode rejected
- ✓ Zero sessions accepted

**Edge Cases (3 tests):**
- ✓ Null times for cmd_enter/exit windows
- ✓ Complete pipeline validation
- ✓ Multiple satellites and gateways

**Result: 22/22 tests passing (100%)**

## Usage Examples

### Standard Validation (Default)

```bash
# Parse OASIS log with validation
python scripts/parse_oasis_log.py data/sample_oasis.log -o data/windows.json
# Output: ✓ Schema validation passed: 2 windows

# Generate scenario with validation
python scripts/gen_scenario.py data/windows.json -o config/scenario.json
# Output: ✓ Scenario validation passed

# Compute metrics with validation
python scripts/metrics.py config/scenario.json -o reports/metrics.csv
# Output: ✓ Metrics validation passed
```

### Skip Validation (Not Recommended)

```bash
# Skip validation for performance-critical situations
python scripts/parse_oasis_log.py data/log.txt --skip-validation
python scripts/gen_scenario.py data/windows.json --skip-validation
python scripts/metrics.py config/scenario.json --skip-validation
```

### Validation Error Examples

**Invalid window type:**
```
ERROR: Invalid windows data: Window validation failed: 'invalid_type' is not one of ['cmd', 'xband', 'cmd_enter', 'cmd_exit', 'tle']
Path: windows.0.type
Schema path: properties.windows.items.properties.type.enum
```

**Missing required field:**
```
ERROR: Output validation failed: Window validation failed: 'sat' is a required property
Path: windows.0
Schema path: required
```

**Invalid time format:**
```
ERROR: Window item validation failed: '2025-10-08 02:00:00' does not match '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(Z|[+-]\\d{2}:\\d{2})$'
Path: start
```

## Schema Features

### Time Format Validation
- Accepts: `2025-10-08T02:00:00Z` (UTC)
- Accepts: `2025-10-08T02:00:00+00:00` (explicit timezone)
- Accepts: `2025-10-08T02:00:00-05:00` (timezone offset)
- Rejects: `2025-10-08 02:00:00` (missing 'T')
- Rejects: `2025/10/08T02:00:00Z` (wrong separators)

### Enum Validation
- Window types: strict enum enforcement
- Relay modes: `transparent`, `regenerative` only
- Event types: `link_up`, `link_down`, `handover`, `failure`, `recovery`
- Propagation models: `free_space`, `two_ray_ground`, `log_distance`

### Numeric Constraints
- Elevation: 0-90° (inclusive)
- Azimuth: 0-360° (inclusive)
- Altitude: 160-50000 km (LEO to GEO)
- Data rate: > 0 (exclusiveMinimum)
- Latency: ≥ 0
- Throughput: ≥ 0

### Conditional Validation
- `cmd`, `xband`, `tle` windows require both `start` and `end`
- `cmd_enter` can have null `end`
- `cmd_exit` can have null `start`
- Empty satellite/gateway arrays rejected
- At least one satellite and gateway required

## Benefits

1. **Early Error Detection**: Invalid data caught at parse time, not during simulation
2. **Clear Error Messages**: Detailed validation errors with JSON path information
3. **Type Safety**: Ensures data types match expected formats
4. **Range Validation**: Prevents physically impossible values (e.g., 91° elevation)
5. **Integration Safety**: Guarantees data contracts between pipeline stages
6. **Documentation**: Schemas serve as machine-readable API documentation
7. **Testing**: Comprehensive test suite ensures validation correctness

## Dependencies

- **jsonschema==4.17.3** (already in requirements.txt)
- Python 3.10+ (for type hints)

## Files Modified

1. **Created:**
   - `config/schemas.py` (520 lines) - Schema definitions and validators
   - `tests/test_schemas.py` (628 lines) - Comprehensive test suite
   - `docs/P0-5-JSON-SCHEMA-VALIDATION.md` (this file)

2. **Modified:**
   - `scripts/parse_oasis_log.py` - Added window validation
   - `scripts/gen_scenario.py` - Added scenario validation
   - `scripts/metrics.py` - Added metrics validation

3. **Verified:**
   - `requirements.txt` - jsonschema already present

## Testing

```bash
# Run schema validation tests
pytest tests/test_schemas.py -v

# Run with coverage
pytest tests/test_schemas.py --cov=config.schemas --cov-report=term

# Test entire pipeline with validation
make test
```

## Future Enhancements

1. **JSON Schema $ref**: Use references for reusable definitions
2. **Custom Formats**: Add custom format validators (e.g., NORAD ID)
3. **Schema Versioning**: Support multiple schema versions
4. **Performance**: Cache compiled schemas for repeated validation
5. **OpenAPI Integration**: Generate OpenAPI specs from schemas
6. **Schema Registry**: Central schema repository for multiple services

## Related Issues

- P0-2: Input validation and sanitization (complements schema validation)
- P0-3: Structured logging (logs validation errors)
- P0-4: Configuration management (validates config files)

## Conclusion

JSON Schema validation provides a robust, standards-based approach to ensuring data integrity throughout the TASA SatNet Pipeline. All invalid inputs are rejected early with clear error messages, preventing downstream errors and improving overall system reliability.

**Status: ✅ COMPLETE**
- All schemas implemented
- Full integration across pipeline
- 22/22 tests passing
- End-to-end validation verified
