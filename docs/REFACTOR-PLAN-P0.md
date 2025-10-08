# P0 Refactoring Plan - Critical Issues

**Date**: 2025-10-08
**Phase**: Refactor (TDD Cycle)
**Priority**: P0 (Critical - Must Fix)
**Timeline**: 1-2 days

---

## 🎯 Objectives

Fix **5 critical P0 issues** identified in code review to ensure:
- ✅ Code quality and maintainability
- ✅ Security and input validation
- ✅ Performance optimization
- ✅ Type safety and correctness

---

## 📋 P0 Issues Summary

| ID | Issue | Module | Impact | Effort |
|----|-------|--------|--------|--------|
| **P0-1** | Timezone parameter misuse | `parse_oasis_log.py` | High | 2h |
| **P0-2** | Missing input validation | All modules | Critical | 3h |
| **P0-3** | Magic numbers in formulas | `gen_scenario.py` | Medium | 2h |
| **P0-4** | O(n²) pairing algorithm | `parse_oasis_log.py` | High | 3h |
| **P0-5** | No JSON Schema validation | All modules | Critical | 4h |

**Total Estimated Effort**: 14 hours (1-2 days with parallel agents)

---

## 🔧 P0-1: Fix Timezone Parameter Usage

### Current Issue
```python
# ❌ parse_oasis_log.py:19-21
def parse_dt(s: str, tz: str = "UTC") -> datetime:
    dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    return dt.replace(tzinfo=timezone.utc)  # ⚠️ 忽略了 tz 參數！
```

### Root Cause
- Function accepts `tz` parameter but never uses it
- Always returns UTC timezone regardless of parameter
- Misleading API contract

### Solution
```python
# ✅ Fixed version
def parse_dt(s: str, tz: str = "UTC") -> datetime:
    """Parse timestamp with configurable timezone."""
    dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    if tz == "UTC":
        return dt.replace(tzinfo=timezone.utc)
    else:
        import pytz
        return pytz.timezone(tz).localize(dt)
```

### Test Plan
```python
def test_parse_dt_with_utc():
    result = parse_dt("2025-10-08T12:00:00Z", tz="UTC")
    assert result.tzinfo == timezone.utc

def test_parse_dt_with_custom_tz():
    result = parse_dt("2025-10-08T12:00:00Z", tz="Asia/Taipei")
    assert result.tzinfo.zone == "Asia/Taipei"
```

---

## 🔧 P0-2: Add Input Validation & Security

### Current Issues
1. **No file size limits** - Could cause OOM with large files
2. **No path traversal protection** - Security vulnerability
3. **No input sanitization** - Injection risks
4. **No error handling** - Silent failures

### Solutions

#### File Size Validation
```python
# config/constants.py
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

def validate_file_size(file_path: Path) -> None:
    """Validate file size is within limits."""
    size = file_path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File too large: {size/1024/1024:.2f}MB "
            f"(max: {MAX_FILE_SIZE_MB}MB)"
        )
```

#### Path Traversal Protection
```python
def validate_file_path(file_path: Path, base_dir: Path) -> Path:
    """Validate file path is within allowed directory."""
    resolved = file_path.resolve()
    if not resolved.is_relative_to(base_dir):
        raise ValueError(f"Path traversal detected: {file_path}")
    return resolved
```

#### Input Sanitization
```python
def sanitize_satellite_name(name: str) -> str:
    """Sanitize satellite name to prevent injection."""
    # Only allow alphanumeric, hyphen, underscore
    import re
    if not re.match(r'^[A-Za-z0-9\-_]+$', name):
        raise ValueError(f"Invalid satellite name: {name}")
    return name
```

### Test Plan
```python
def test_file_size_limit():
    # Create 101MB file
    with pytest.raises(ValueError, match="File too large"):
        validate_file_size(large_file)

def test_path_traversal():
    with pytest.raises(ValueError, match="Path traversal"):
        validate_file_path(Path("../../etc/passwd"), Path("/data"))

def test_input_sanitization():
    assert sanitize_satellite_name("SAT-123") == "SAT-123"
    with pytest.raises(ValueError):
        sanitize_satellite_name("SAT'; DROP TABLE--")
```

---

## 🔧 P0-3: Replace Magic Numbers with Constants

### Current Issues
```python
# ❌ gen_scenario.py:119-124
def _compute_base_latency(self) -> float:
    if self.mode == 'transparent':
        return 5.0  # ms - 魔術數字
    else:
        return 10.0  # ms - 魔術數字
```

### Solution
```python
# config/constants.py
class LatencyConstants:
    """Physical and processing latency constants."""

    # Speed of light (km/s)
    SPEED_OF_LIGHT_KM_S = 299_792.458

    # Processing delays (ms)
    TRANSPARENT_PROCESSING_MS = 5.0
    REGENERATIVE_PROCESSING_MS = 10.0

    # Queuing delays (ms)
    MIN_QUEUING_DELAY_MS = 0.5
    MAX_QUEUING_DELAY_MS = 2.0

    # Transmission delays
    PACKET_SIZE_BYTES = 1500
    DEFAULT_BANDWIDTH_MBPS = 100

# gen_scenario.py
from config.constants import LatencyConstants

def _compute_base_latency(self) -> float:
    if self.mode == 'transparent':
        return LatencyConstants.TRANSPARENT_PROCESSING_MS
    else:
        return LatencyConstants.REGENERATIVE_PROCESSING_MS
```

### Test Plan
```python
def test_latency_constants():
    assert LatencyConstants.SPEED_OF_LIGHT_KM_S == 299_792.458
    assert LatencyConstants.TRANSPARENT_PROCESSING_MS == 5.0

def test_compute_latency_uses_constants():
    # Verify no magic numbers in computation
    import ast
    with open("scripts/gen_scenario.py") as f:
        tree = ast.parse(f.read())
    # Check for numeric literals in latency functions
    assert no_magic_numbers_in_function(tree, "_compute_base_latency")
```

---

## 🔧 P0-4: Optimize O(n²) Pairing Algorithm

### Current Issue
```python
# ❌ parse_oasis_log.py:52-64 - O(n²)
for i, w in enters:
    for j, x in exits:
        if j in used_exits:
            continue
        if x["sat"]==w["sat"] and x["gw"]==w["gw"]:
            paired.append(...)
            used_exits.add(j)
            break
```

**Complexity**: O(n²) where n = number of windows
**Problem**: Slow for large datasets (1000+ windows)

### Solution - O(n) with Hash Map
```python
# ✅ Optimized version - O(n)
def pair_windows_optimized(enters: list, exits: list) -> list:
    """Pair enter/exit windows in O(n) time."""
    paired = []

    # Build hash map: (sat, gw) -> list of exit windows
    exit_map = {}
    for idx, exit_win in exits:
        key = (exit_win["sat"], exit_win["gw"])
        if key not in exit_map:
            exit_map[key] = []
        exit_map[key].append((idx, exit_win))

    # Match enters with exits in O(1) lookup
    for enter_idx, enter_win in enters:
        key = (enter_win["sat"], enter_win["gw"])

        if key in exit_map and exit_map[key]:
            exit_idx, exit_win = exit_map[key].pop(0)

            paired.append({
                "type": "contact_window",
                "start": enter_win["time"],
                "end": exit_win["time"],
                "sat": enter_win["sat"],
                "gw": enter_win["gw"]
            })

    return paired
```

**New Complexity**: O(n)
**Speedup**: 100x faster for n=1000

### Benchmark Test
```python
@pytest.mark.benchmark
def test_pairing_performance(benchmark):
    # Generate 1000 enter/exit pairs
    enters = [(i, {"sat": f"SAT-{i}", "gw": "GW1", "time": f"...{i}"})
              for i in range(1000)]
    exits = [(i, {"sat": f"SAT-{i}", "gw": "GW1", "time": f"...{i+1}"})
             for i in range(1000)]

    result = benchmark(pair_windows_optimized, enters, exits)

    # Should complete in < 10ms (vs 1000ms for O(n²))
    assert benchmark.stats['mean'] < 0.01  # 10ms
```

---

## 🔧 P0-5: Add JSON Schema Validation

### Current Issue
- No validation of input JSON structure
- Silent failures on malformed data
- Type errors discovered at runtime

### Solution - JSON Schema
```python
# config/schemas.py
OASIS_WINDOW_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["type", "time", "sat", "gw"],
    "properties": {
        "type": {
            "type": "string",
            "enum": ["enter_command_window", "exit_command_window",
                     "enter_data_link", "exit_data_link"]
        },
        "time": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$"
        },
        "sat": {"type": "string", "minLength": 1},
        "gw": {"type": "string", "minLength": 1},
        "elevation_deg": {"type": "number", "minimum": 0, "maximum": 90}
    }
}

SCENARIO_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["satellites", "gateways", "mode"],
    "properties": {
        "satellites": {
            "type": "array",
            "items": {"type": "string"}
        },
        "gateways": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "beams"],
                "properties": {
                    "name": {"type": "string"},
                    "beams": {"type": "integer", "minimum": 1}
                }
            }
        },
        "mode": {
            "type": "string",
            "enum": ["transparent", "regenerative"]
        }
    }
}

# Validation function
import jsonschema

def validate_windows(data: dict) -> None:
    """Validate OASIS window data against schema."""
    try:
        jsonschema.validate(instance=data, schema=OASIS_WINDOW_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Invalid window data: {e.message}")

def validate_scenario(data: dict) -> None:
    """Validate scenario data against schema."""
    try:
        jsonschema.validate(instance=data, schema=SCENARIO_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Invalid scenario data: {e.message}")
```

### Test Plan
```python
def test_valid_window_passes():
    valid = {
        "type": "enter_command_window",
        "time": "2025-10-08T12:00:00Z",
        "sat": "SAT-1",
        "gw": "HSINCHU"
    }
    validate_windows(valid)  # Should not raise

def test_invalid_window_fails():
    invalid = {"type": "invalid_type", "sat": "SAT-1"}
    with pytest.raises(ValueError, match="Invalid window data"):
        validate_windows(invalid)

def test_schema_validates_time_format():
    invalid = {
        "type": "enter_command_window",
        "time": "invalid-time",  # Wrong format
        "sat": "SAT-1",
        "gw": "HSINCHU"
    }
    with pytest.raises(ValueError):
        validate_windows(invalid)
```

---

## 🚀 Execution Plan

### Parallel Agent Tasks

**Agent 1: Timezone & Validation Expert**
- Task: Fix P0-1 (timezone) and P0-2 (validation)
- Files: `parse_oasis_log.py`, create `config/validators.py`
- Tests: `tests/test_validators.py`

**Agent 2: Constants & Configuration Specialist**
- Task: Fix P0-3 (magic numbers)
- Files: Create `config/constants.py`, update `gen_scenario.py`, `metrics.py`
- Tests: `tests/test_constants.py`

**Agent 3: Algorithm Optimization Expert**
- Task: Fix P0-4 (O(n²) → O(n))
- Files: `parse_oasis_log.py`
- Tests: `tests/test_parser_performance.py` (benchmarks)

**Agent 4: Schema Validation Architect**
- Task: Fix P0-5 (JSON Schema)
- Files: Create `config/schemas.py`, update all modules
- Tests: `tests/test_schemas.py`

**Agent 5: Test Coverage Specialist**
- Task: Ensure all P0 fixes have 90%+ coverage
- Files: Update all test files
- Verify: Coverage report shows ≥90% for modified modules

### Execution Order
1. **Parallel Phase** (All agents work simultaneously)
   - Agent 1-4: Implement P0 fixes
   - Agent 5: Write comprehensive tests

2. **Integration Phase** (Sequential)
   - Merge all changes
   - Run full test suite
   - Verify coverage ≥90%

3. **Validation Phase**
   - Run benchmarks
   - Check for regressions
   - Update documentation

---

## ✅ Success Criteria

### Code Quality
- [ ] All 5 P0 issues fixed
- [ ] No magic numbers in code
- [ ] All functions have type hints
- [ ] Input validation on all external data

### Performance
- [ ] Pairing algorithm: O(n) instead of O(n²)
- [ ] Benchmark: 1000 windows in < 10ms

### Testing
- [ ] Test coverage ≥ 90% for all modified files
- [ ] All tests passing (100%)
- [ ] Performance benchmarks passing

### Security
- [ ] File size limits enforced
- [ ] Path traversal protection
- [ ] Input sanitization active
- [ ] JSON Schema validation enabled

---

## 📊 Metrics

### Before Refactoring
- Magic numbers: 12+ instances
- Type coverage: ~60%
- Input validation: 0%
- Pairing complexity: O(n²)
- Test coverage: 27.42% (new modules)

### After Refactoring (Target)
- Magic numbers: 0
- Type coverage: 100%
- Input validation: 100%
- Pairing complexity: O(n)
- Test coverage: ≥90%

---

## 🔄 Next Steps After P0

1. **P1 Issues** (Week 2)
   - Centralized config management
   - Logging infrastructure
   - Error message improvements

2. **Integration** (Week 2-3)
   - Connect TLE → OASIS pipeline
   - Multi-constellation integration
   - Visualization in metrics output

3. **K8s Update** (Week 3)
   - Deploy refactored pipeline
   - Validate at scale
   - Update documentation

---

**Status**: 📝 Plan Created - Ready for Execution
**Next Action**: Spawn 5 parallel agents to implement P0 fixes
