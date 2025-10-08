# TDD Workflow Guide - TASA SatNet Pipeline

## Test-Driven Development (TDD) Philosophy

### Core Principle
**Write tests first, make them pass, then refactor.** 

No code goes to production unless tests pass with >90% coverage.

---

## TDD Cycle (Red-Green-Refactor)

### 1. RED - Write a Failing Test
```python
# tests/test_new_feature.py
def test_new_feature():
    """Test description of expected behavior."""
    result = new_feature(input_data)
    assert result == expected_output
```

**Run test:** It should FAIL (RED)
```bash
pytest tests/test_new_feature.py -v
# Expected: FAILED - function new_feature doesn't exist yet
```

### 2. GREEN - Make the Test Pass
```python
# scripts/new_module.py
def new_feature(input_data):
    """Minimal implementation to pass the test."""
    return expected_output  # Simplest possible implementation
```

**Run test:** It should PASS (GREEN)
```bash
pytest tests/test_new_feature.py -v
# Expected: PASSED
```

### 3. REFACTOR - Improve the Code
```python
# scripts/new_module.py
def new_feature(input_data):
    """Improved implementation with proper logic."""
    # Add real logic here
    # Optimize, clean up, add error handling
    return processed_result
```

**Run test:** Should still PASS
```bash
pytest tests/test_new_feature.py -v
# Expected: PASSED (tests ensure refactoring didn't break anything)
```

---

## TDD Workflow for TASA SatNet Pipeline

### Phase 0: Parser Development (Example)

#### Step 1: Write Test for Timestamp Parsing
```python
# tests/test_parser.py
def test_parse_valid_timestamp():
    """Test parsing valid ISO 8601 timestamp."""
    ts = "2025-01-08T10:15:30Z"
    result = parse_dt(ts)
    assert isinstance(result, datetime)
    assert result.year == 2025
    # ... more assertions
```

#### Step 2: Run Test (Should Fail)
```bash
pytest tests/test_parser.py::test_parse_valid_timestamp -v
# FAILED - parse_dt function doesn't exist
```

#### Step 3: Implement Function
```python
# scripts/parse_oasis_log.py
from datetime import datetime, timezone

def parse_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
```

#### Step 4: Run Test (Should Pass)
```bash
pytest tests/test_parser.py::test_parse_valid_timestamp -v
# PASSED ✓
```

#### Step 5: Add Edge Cases
```python
def test_parse_invalid_timestamp():
    """Test parsing invalid timestamp raises ValueError."""
    with pytest.raises(ValueError):
        parse_dt("INVALID-TIMESTAMP")
```

#### Step 6: Run All Tests
```bash
pytest tests/test_parser.py -v --cov=scripts
# All tests should pass with good coverage
```

---

## Testing Levels

### 1. Unit Tests (Required)
**Test individual functions and methods in isolation.**

```python
# tests/test_parser.py
def test_regex_pattern_enter_command():
    """Test enter command window pattern matching."""
    line = "enter command window @ 2025-01-08T10:15:30Z sat=SAT-1 gw=HSINCHU"
    match = PAT_ENTER.search(line)
    assert match is not None
    assert match.group(2) == "SAT-1"
```

**Coverage Target:** >90%

### 2. Integration Tests (Required for complex flows)
**Test components working together.**

```python
# tests/test_integration.py
@pytest.mark.integration
def test_full_parsing_pipeline(tmp_path):
    """Test complete log parsing pipeline."""
    # Create test log file
    log_file = tmp_path / "test.log"
    log_file.write_text(sample_log_content)
    
    # Run parser
    output_file = tmp_path / "output.json"
    parse_log(log_file, output_file)
    
    # Validate output
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert data["meta"]["count"] == 4
```

### 3. Benchmark Tests (Optional)
**Test performance requirements.**

```python
# tests/test_performance.py
@pytest.mark.benchmark
def test_parse_large_log_performance(benchmark):
    """Test parsing 10K lines completes in <5 seconds."""
    result = benchmark(parse_large_log)
    assert result.time < 5.0
```

### 4. Docker Tests (For deployment validation)
**Test in containerized environment.**

```python
# tests/test_docker.py
@pytest.mark.docker
def test_parser_in_docker():
    """Test parser runs correctly in Docker."""
    result = docker_client.containers.run(
        "tasa-satnet-pipeline:latest",
        "python scripts/parse_oasis_log.py data/sample.log"
    )
    assert result.exit_code == 0
```

### 5. Kubernetes Tests (For K8s deployment)
**Test K8s deployment and jobs.**

```python
# tests/test_k8s.py
@pytest.mark.k8s
def test_parser_job_in_k8s():
    """Test parser Job completes successfully in K8s."""
    # Apply job manifest
    kubectl.apply("k8s/job-parser.yaml")
    
    # Wait for completion
    job_status = kubectl.wait_for_job("tasa-parser-job", timeout=300)
    assert job_status == "Complete"
```

---

## Running Tests

### Local Development

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_parser.py -v

# Run specific test function
pytest tests/test_parser.py::test_parse_valid_timestamp -v

# Run with coverage
pytest tests/ --cov=scripts --cov-report=html

# Run only fast tests (skip slow, docker, k8s)
pytest tests/ -v -m "not slow and not docker and not k8s"

# Run only unit tests
pytest tests/ -v -m "unit"

# Run integration tests
pytest tests/ -v -m "integration"
```

### Windows (PowerShell)

```powershell
# Run test script
.\scripts\run_tests.ps1

# Run with benchmarks
.\scripts\run_tests.ps1 -RunBenchmarks
```

### Linux/Mac (Bash)

```bash
# Make script executable
chmod +x scripts/run_tests.sh

# Run test script
./scripts/run_tests.sh

# Run with benchmarks
RUN_BENCHMARKS=true ./scripts/run_tests.sh
```

### Docker

```bash
# Build image
docker build -t tasa-satnet-pipeline:latest .

# Run tests in container
docker-compose --profile testing up test-runner

# Or run directly
docker run --rm tasa-satnet-pipeline:latest pytest tests/ -v
```

### Kubernetes

```bash
# Run test job
kubectl apply -f k8s/job-test.yaml

# Check results
kubectl logs -f -n tasa-satnet job/tasa-test-job

# Get job status
kubectl get job -n tasa-satnet tasa-test-job
```

---

## Coverage Requirements

### Minimum Coverage: 90%

```bash
# Run tests with coverage enforcement
pytest tests/ --cov=scripts --cov-fail-under=90

# Generate HTML coverage report
pytest tests/ --cov=scripts --cov-report=html
# Open htmlcov/index.html in browser
```

### Coverage Exemptions

Some code may be exempt from coverage:
- Debugging code (marked with `# pragma: no cover`)
- OS-specific code paths
- External dependencies
- Main entry points (if statement)

Example:
```python
if __name__ == "__main__":  # pragma: no cover
    main()
```

---

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_parser.py           # Parser unit tests
├── test_parser_integration.py  # Parser integration tests
├── test_scenario_generator.py  # Scenario gen tests
├── test_metrics.py          # Metrics calculator tests
├── test_scheduler.py        # Scheduler tests
├── fixtures/                # Test data
│   ├── valid_log.txt
│   ├── malformed_log.txt
│   └── edge_cases.txt
├── integration/             # Integration test suites
│   └── test_full_pipeline.py
└── benchmarks/              # Performance tests
    └── test_performance.py
```

### Test Naming Convention

```python
# Test files: test_<module>.py
# Test classes: Test<Feature>
# Test functions: test_<what_is_being_tested>

# Good examples:
def test_parse_valid_timestamp()
def test_parse_invalid_timestamp_raises_error()
def test_regex_matches_enter_command()

# Bad examples:
def test1()  # Not descriptive
def testTimestamp()  # Wrong naming convention
def test_everything()  # Too broad
```

---

## Continuous Integration

### Pre-commit Checks

```bash
# Install pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
pytest tests/ -v --cov=scripts --cov-fail-under=90 || {
    echo "Tests failed! Commit blocked."
    exit 1
}
EOF

chmod +x .git/hooks/pre-commit
```

### CI Pipeline (GitHub Actions)

```yaml
name: Test Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          pytest tests/ -v \
            --cov=scripts \
            --cov-report=xml \
            --cov-fail-under=90
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## TDD Best Practices

### 1. Write Tests First
- Define expected behavior before writing code
- Forces you to think about API design
- Ensures testability from the start

### 2. Test One Thing at a Time
```python
# Good: Tests one specific behavior
def test_parse_timestamp_with_timezone():
    result = parse_dt("2025-01-08T10:15:30Z")
    assert result.tzinfo == timezone.utc

# Bad: Tests multiple things
def test_parse_and_format_and_validate_timestamp():
    # Too many responsibilities
    pass
```

### 3. Use Descriptive Test Names
```python
# Good
def test_parse_invalid_timestamp_raises_ValueError():
    pass

# Bad
def test_parse_error():
    pass
```

### 4. Arrange-Act-Assert Pattern
```python
def test_example():
    # Arrange: Set up test data
    input_data = create_test_input()
    
    # Act: Execute the code under test
    result = function_under_test(input_data)
    
    # Assert: Verify the results
    assert result == expected_output
```

### 5. Use Fixtures for Common Setup
```python
# conftest.py
@pytest.fixture
def sample_log_file(tmp_path):
    """Create a sample log file for testing."""
    log_file = tmp_path / "test.log"
    log_file.write_text(SAMPLE_LOG_CONTENT)
    return log_file

# test_parser.py
def test_parser(sample_log_file):
    """Test parser with fixture."""
    result = parse_log(sample_log_file)
    assert result is not None
```

### 6. Test Edge Cases
- Empty input
- Invalid input
- Boundary values
- Null/None values
- Large inputs
- Concurrent operations

### 7. Keep Tests Fast
- Mock external dependencies
- Use in-memory databases
- Avoid unnecessary I/O
- Run slow tests separately (`@pytest.mark.slow`)

---

## Debugging Failed Tests

### View Detailed Output
```bash
# Show full output
pytest tests/test_parser.py -vv

# Show local variables on failure
pytest tests/test_parser.py -l

# Stop on first failure
pytest tests/test_parser.py -x

# Drop into debugger on failure
pytest tests/test_parser.py --pdb
```

### Analyze Coverage Gaps
```bash
# Generate coverage report
pytest --cov=scripts --cov-report=html

# Open in browser
start htmlcov/index.html  # Windows
open htmlcov/index.html   # Mac
xdg-open htmlcov/index.html  # Linux
```

---

## TDD Checklist

Before committing code, ensure:

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Coverage >90% (`pytest --cov-fail-under=90`)
- [ ] No linting errors (`flake8 scripts/ tests/`)
- [ ] Type checking passes (`mypy scripts/`)
- [ ] Tests are descriptive and well-organized
- [ ] Edge cases are covered
- [ ] Integration tests pass
- [ ] Documentation updated if needed
- [ ] Docker build succeeds
- [ ] K8s deployments tested (if applicable)

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [TDD by Example (Kent Beck)](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)
- [Effective Python Testing with Pytest](https://realpython.com/pytest-python-testing/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

---

**Remember: No code ships without passing tests!**
