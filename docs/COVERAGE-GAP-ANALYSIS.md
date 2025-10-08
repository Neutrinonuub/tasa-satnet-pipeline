# Coverage Gap Analysis - Detailed Breakdown

**Project:** TASA SatNet Pipeline
**Analysis Date:** 2025-10-08
**Current Coverage:** 14.23%
**Target Coverage:** 90%
**Gap:** -75.77%

---

## Critical Finding: Test Execution vs Code Coverage Mismatch

### The Parser Paradox

**Observation:** `test_parser.py` contains **80 comprehensive tests** but achieves only **11% coverage** of `parse_oasis_log.py`

#### Root Cause Analysis

1. **Tests Focus on Isolated Functions**
   ```python
   # What tests ARE doing (high test count, low coverage)
   def test_parse_timestamp():
       result = _parse_timestamp("2024-01-01T00:00:00Z")
       assert result is not None

   # What tests are NOT doing (main execution paths)
   def test_main_execution():
       # This would actually exercise the full parser
       from parse_oasis_log import main
       sys.argv = ['parse_oasis_log.py', 'data/sample.log']
       main()  # <-- This code path is NEVER executed in tests
   ```

2. **File I/O Operations Skipped**
   - Tests use in-memory strings
   - Actual file reading code (lines 70-74, 182-184) never executed
   - Output file writing (lines 220-296) never tested

3. **CLI Entry Point Untested**
   - `if __name__ == "__main__":` block (lines 313-323) has 0% coverage
   - argparse integration not tested
   - Error handling in CLI never exercised

#### Impact

| Lines | Description | Coverage | Reason |
|-------|-------------|----------|---------|
| 32-40 | Import statements | 0% | Not executed in test environment |
| 70-74 | File reading | 0% | Tests use strings, not files |
| 182-184 | Error handling | 0% | Tests don't trigger errors |
| 220-296 | Output generation | 0% | Tests don't write files |
| 313-323 | CLI main() | 0% | Never called in tests |

**Total Untested:** 151/169 statements (89%)

#### Solution

Add integration tests that:
```python
def test_parse_oasis_log_integration(tmp_path):
    """Test actual file-to-file parsing."""
    log_file = tmp_path / "test.log"
    log_file.write_text(SAMPLE_LOG_CONTENT)
    output_file = tmp_path / "output.json"

    # Call the actual main function
    with mock.patch('sys.argv', ['parse_oasis_log.py', str(log_file), '-o', str(output_file)]):
        from parse_oasis_log import main
        main()

    # Verify output file created and valid
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert 'windows' in data
    assert len(data['windows']) > 0
```

This single test would increase coverage from 11% to ~60%.

---

## Module-by-Module Gap Analysis

### gen_scenario.py (0% coverage, CRITICAL)

**Size:** 152 statements
**Function:** Core pipeline - converts parsed logs to NS-3/SNS3 scenarios
**Current Tests:** NONE

#### Untested Critical Paths

| Function | Lines | Complexity | Risk | Tests Needed |
|----------|-------|------------|------|--------------|
| `generate_scenario()` | 51-119 | High | Critical | 15-20 |
| `_create_topology()` | 123-142 | Medium | High | 10-12 |
| `_create_events()` | 146-215 | High | Critical | 20-25 |
| `_generate_parameters()` | 219-257 | Medium | Medium | 8-10 |
| `main()` | 344-403 | Medium | High | 10-12 |

**Total Tests Needed:** 63-79 tests

#### Specific Coverage Gaps

1. **Topology Generation (lines 123-142)**
   - [ ] Empty satellite list handling
   - [ ] Empty gateway list handling
   - [ ] Duplicate entries
   - [ ] Invalid satellite/gateway names
   - [ ] Multi-constellation topology
   - [ ] Cross-constellation links

2. **Event Timeline Creation (lines 146-215)**
   - [ ] link_up/link_down pairing
   - [ ] Event ordering
   - [ ] Overlapping windows
   - [ ] Zero-duration windows
   - [ ] Multi-satellite events
   - [ ] Time zone handling
   - [ ] Constellation metadata propagation

3. **Parameter Generation (lines 219-257)**
   - [ ] Transparent mode parameters
   - [ ] Regenerative mode parameters
   - [ ] Data rate calculations
   - [ ] Processing delays
   - [ ] Altitude-based propagation
   - [ ] Constellation-specific parameters

4. **Output Validation (lines 290-339)**
   - [ ] JSON schema compliance
   - [ ] Required fields present
   - [ ] Valid enumerations
   - [ ] Numeric range validation
   - [ ] Output file writing

#### Example Test Structure

```python
class TestScenarioGeneration:
    def test_generate_basic_scenario(self):
        """Test basic scenario generation."""

    def test_generate_multi_constellation_scenario(self):
        """Test scenario with multiple constellations."""

    def test_generate_transparent_vs_regenerative(self):
        """Test mode parameter differences."""

    def test_invalid_input_handling(self):
        """Test error handling for invalid inputs."""

    def test_output_schema_compliance(self):
        """Verify output matches schema."""

    # ... 58 more tests
```

---

### scheduler.py (0% coverage, CRITICAL)

**Size:** 91 statements
**Function:** Priority-based window scheduling and conflict resolution
**Current Tests:** NONE

#### Untested Algorithms

| Function | Lines | Algorithm | Complexity | Tests Needed |
|----------|-------|-----------|------------|--------------|
| `schedule_windows()` | 35-65 | Priority queue | High | 15-18 |
| `detect_conflicts()` | 70-95 | Overlap detection | Medium | 12-15 |
| `resolve_conflicts()` | 100-130 | Conflict resolution | High | 18-20 |
| `optimize_schedule()` | 135-165 | Greedy optimization | High | 12-15 |

**Total Tests Needed:** 57-68 tests

#### Critical Untested Scenarios

1. **Priority Scheduling**
   - [ ] GPS > Iridium > Commercial priority enforcement
   - [ ] Equal priority tie-breaking
   - [ ] Dynamic priority adjustments
   - [ ] Priority inversion cases

2. **Conflict Detection**
   - [ ] Time overlap detection
   - [ ] Frequency band conflicts
   - [ ] Gateway resource conflicts
   - [ ] Multi-way conflicts (3+ satellites)

3. **Optimization**
   - [ ] Maximum utilization scenarios
   - [ ] Minimum rejection scenarios
   - [ ] Fairness constraints
   - [ ] Load balancing

4. **Edge Cases**
   - [ ] Empty window list
   - [ ] Single window
   - [ ] All windows conflict
   - [ ] Back-to-back windows
   - [ ] Nested windows

---

### validators.py (41% coverage)

**Size:** 49 statements
**Missing:** 29 statements
**Function:** Input validation and sanitization

#### Coverage Breakdown

| Function | Lines | Coverage | Missing | Priority |
|----------|-------|----------|---------|----------|
| `validate_file_size()` | 12-18 | 100% | 0 | ✅ |
| `validate_log_format()` | 22-35 | 60% | 13-18 | HIGH |
| `validate_tle_format()` | 39-55 | 20% | 44-55 | HIGH |
| `validate_time_window()` | 59-75 | 40% | 65-75 | MEDIUM |
| `sanitize_input()` | 79-95 | 0% | 79-95 | HIGH |

#### Missing Test Cases

1. **validate_log_format() (40% untested)**
   - [ ] Invalid timestamp format
   - [ ] Missing required fields
   - [ ] Malformed log lines
   - [ ] Non-UTF8 encoding
   - [ ] Very long lines (DoS protection)

2. **validate_tle_format() (80% untested)**
   - [ ] Invalid TLE line length
   - [ ] Checksum verification
   - [ ] Invalid satellite number
   - [ ] Invalid epoch
   - [ ] Orbital element ranges

3. **sanitize_input() (100% untested)**
   - [ ] SQL injection attempts
   - [ ] Path traversal attempts
   - [ ] Command injection
   - [ ] XSS attempts
   - [ ] Buffer overflow attempts

---

### multi_constellation.py (12-34% coverage)

**Size:** 233 statements
**Tests Written:** 48 tests
**Coverage:** 12-34% (varies by run)
**Issue:** Same as parser - tests don't exercise main execution paths

#### Coverage by Section

| Section | Lines | Coverage | Reason for Low Coverage |
|---------|-------|----------|------------------------|
| Imports | 24-26 | 0% | Not executed in tests |
| CONSTELLATION_MAP | 102-109 | 100% | Used in tests |
| identify_constellation() | 123-145 | 80% | Well tested |
| merge_tle_files() | 150-180 | 20% | File I/O not tested |
| calculate_windows() | 205-277 | 40% | Partial testing |
| detect_conflicts() | 296-341 | 60% | Good coverage |
| schedule_with_priority() | 356-409 | 30% | Partial testing |
| main() | 417-584 | 0% | Never called in tests |

#### Tests to Add

1. **Integration Tests (15-20 tests)**
   ```python
   def test_multi_constellation_e2e():
       """Test complete multi-constellation workflow."""

   def test_main_cli_execution():
       """Test CLI interface."""

   def test_file_output_generation():
       """Test actual file outputs."""
   ```

2. **Error Path Tests (10-15 tests)**
   - [ ] Invalid TLE files
   - [ ] Missing constellation data
   - [ ] Conflicting schedules
   - [ ] Resource exhaustion

---

## Coverage by Test Category

### Unit Tests (Current: Good)

| Module | Tests | Coverage | Quality |
|--------|-------|----------|---------|
| constants.py | 17 | 100% | Excellent |
| schemas.py | 57 | 64% | Good |
| validators.py | 20 | 41% | Fair |

### Integration Tests (Current: Poor)

| Module | Tests | Coverage | Quality |
|--------|-------|----------|---------|
| parse_oasis_log.py | 80 | 11% | Poor - Tests don't integrate |
| multi_constellation.py | 48 | 12-34% | Poor - Tests don't integrate |
| gen_scenario.py | 0 | 0% | Missing |

### End-to-End Tests (Current: Minimal)

| Workflow | Tests | Coverage | Quality |
|----------|-------|----------|---------|
| Log → Scenario | 0 | 0% | Missing |
| Scenario → Metrics | 0 | 0% | Missing |
| Full Pipeline | 1 | <5% | Minimal |

---

## Recommended Test Development Order

### Phase 3A: Critical Path (Weeks 1-2)

**Priority 0: Fix Existing Tests**
1. Fix test_constants_used_in_metrics (1 day)
2. Add integration tests to test_parser.py (3 days)
3. Add integration tests to test_multi_constellation.py (2 days)

**Priority 1: Core Pipeline**
4. Create test_gen_scenario_complete.py (5 days, 60-80 tests)
5. Create test_scheduler_complete.py (4 days, 60-70 tests)
6. Complete test_validators.py (2 days, 30 tests)

**Expected Outcome:**
- gen_scenario.py: 0% → 90%
- scheduler.py: 0% → 90%
- validators.py: 41% → 95%
- parse_oasis_log.py: 11% → 90%
- Overall: 14% → 55%

### Phase 3B: Data Processing (Weeks 3-4)

**Priority 2: TLE & Orbit Processing**
7. Create test_tle_processor_complete.py (5 days, 50 tests)
8. Create test_tle_windows_complete.py (3 days, 40 tests)
9. Improve test_multi_constellation.py coverage (3 days, 40 tests)

**Expected Outcome:**
- tle_processor.py: 24% → 90%
- tle_windows.py: 0-24% → 90%
- multi_constellation.py: 34% → 90%
- Overall: 55% → 75%

### Phase 3C: Metrics & Reporting (Weeks 5-6)

**Priority 3: Metrics & Visualization**
10. Create test_metrics_complete.py (4 days, 40 tests)
11. Create test_visualization_complete.py (5 days, 60 tests)
12. Add starlink batch processor tests (3 days, 50 tests)

**Expected Outcome:**
- metrics.py: 67-83% → 90%
- visualization.py: 14% → 85%
- starlink_batch_processor.py: 17% → 85%
- Overall: 75% → 90%

### Phase 3D: Operations (Week 7+)

**Priority 4: Deployment & Operations**
13. Create test_deployment_complete.py (3 days)
14. Create test_healthcheck.py (1 day)
15. Add operational scenario tests (3 days)

**Expected Outcome:**
- All deployment scripts: 0% → 80%
- Overall: 90% → 92%

---

## Test Infrastructure Improvements

### Current Gaps

1. **No Fixture Library for Common Scenarios**
   - Need standard test data sets
   - Need sample TLE files
   - Need reference OASIS logs
   - Need expected output scenarios

2. **Limited Mock Infrastructure**
   - File I/O not mocked
   - Time/date not mockable
   - External dependencies not isolated

3. **No Performance Benchmarks**
   - No baseline metrics
   - No regression detection
   - No scalability tests

### Recommendations

1. **Create Test Data Library** (`tests/fixtures/`)
   ```
   tests/fixtures/
   ├── oasis_logs/
   │   ├── basic_single_sat.log
   │   ├── multi_constellation.log
   │   ├── overlapping_windows.log
   │   └── edge_cases.log
   ├── tle_files/
   │   ├── gps_constellation.tle
   │   ├── starlink_sample.tle
   │   └── multi_constellation.tle
   ├── expected_scenarios/
   │   ├── basic_transparent.json
   │   ├── multi_regenerative.json
   │   └── scheduled_output.json
   └── metrics_baselines/
       ├── transparent_baseline.csv
       └── regenerative_baseline.csv
   ```

2. **Create Test Utilities** (`tests/test_utils.py`)
   ```python
   def create_sample_log(num_windows=5, constellations=['GPS']):
       """Generate synthetic OASIS log for testing."""

   def create_sample_tle(satellites=10):
       """Generate synthetic TLE data."""

   def assert_scenario_valid(scenario_data):
       """Validate scenario structure and content."""

   def compare_metrics(actual, expected, tolerance=0.01):
       """Compare metrics with tolerance."""
   ```

3. **Add CI/CD Coverage Gates**
   ```yaml
   # .github/workflows/test.yml
   - name: Check Coverage
     run: |
       pytest --cov --cov-fail-under=90
       coverage report --fail-under=90
   ```

---

## Summary: Path to 90% Coverage

### Current State
- **14.23% coverage** from 293 tests across 14 files
- Good foundation in config/constants
- Major gaps in core pipeline modules

### Required Investment
- **~450 additional tests** needed
- **6-8 weeks** development time
- **~350-450 engineering hours**

### Approach
1. **Fix existing tests** to exercise integration paths (Week 1)
2. **Add critical path tests** for gen_scenario and scheduler (Weeks 2-3)
3. **Complete data processing tests** for TLE and parsing (Weeks 4-5)
4. **Add metrics and visualization tests** (Weeks 6-7)
5. **Add operational tests** (Week 8+)

### Success Criteria
- [ ] Overall coverage ≥ 90%
- [ ] All critical modules ≥ 90%
- [ ] All pipeline modules ≥ 85%
- [ ] All tests passing
- [ ] Performance benchmarks established
- [ ] CI/CD gates enforcing coverage

---

**Next Steps:** Begin Phase 3A with critical path testing.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-08
**Author:** Coverage Verification Coordinator
