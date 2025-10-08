#!/usr/bin/env bash
# Test runner script with TDD enforcement

set -euo pipefail

echo "======================================"
echo "TASA SatNet Pipeline - Test Runner"
echo "TDD: Tests must pass before deployment"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "Python version: $(python --version)"
echo "Pytest version: $(pytest --version)"
echo ""

# Run linting first
echo "======================================"
echo "Step 1: Code Linting"
echo "======================================"
if command -v flake8 &> /dev/null; then
    echo "Running flake8..."
    flake8 scripts/ tests/ --max-line-length=100 --statistics || {
        echo -e "${RED}✗ Linting failed!${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Linting passed${NC}"
else
    echo -e "${YELLOW}⚠ flake8 not installed, skipping linting${NC}"
fi
echo ""

# Run type checking
echo "======================================"
echo "Step 2: Type Checking"
echo "======================================"
if command -v mypy &> /dev/null; then
    echo "Running mypy..."
    mypy scripts/ --ignore-missing-imports || {
        echo -e "${YELLOW}⚠ Type checking failed (non-blocking)${NC}"
    }
else
    echo -e "${YELLOW}⚠ mypy not installed, skipping type checking${NC}"
fi
echo ""

# Run unit tests
echo "======================================"
echo "Step 3: Unit Tests"
echo "======================================"
pytest tests/ -v \
    -m "not slow and not integration and not docker and not k8s" \
    --cov=scripts \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=xml \
    --cov-fail-under=90 || {
    echo -e "${RED}✗ Unit tests failed!${NC}"
    echo -e "${RED}Tests must pass before deployment (TDD principle)${NC}"
    exit 1
}
echo -e "${GREEN}✓ Unit tests passed${NC}"
echo ""

# Run integration tests (if available)
echo "======================================"
echo "Step 4: Integration Tests"
echo "======================================"
if pytest tests/ -m "integration" --collect-only &> /dev/null; then
    pytest tests/ -v -m "integration" || {
        echo -e "${YELLOW}⚠ Integration tests failed (non-blocking)${NC}"
    }
else
    echo "No integration tests found, skipping..."
fi
echo ""

# Run benchmark tests (if requested)
if [ "${RUN_BENCHMARKS:-false}" = "true" ]; then
    echo "======================================"
    echo "Step 5: Benchmark Tests"
    echo "======================================"
    pytest tests/ -m "benchmark" --benchmark-only || {
        echo -e "${YELLOW}⚠ Benchmark tests failed (non-blocking)${NC}"
    }
    echo ""
fi

# Generate coverage report
echo "======================================"
echo "Test Coverage Summary"
echo "======================================"
coverage report --show-missing
echo ""
echo "Detailed HTML coverage report: htmlcov/index.html"
echo ""

# Check coverage threshold
COVERAGE=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
if (( $(echo "$COVERAGE < 90" | bc -l) )); then
    echo -e "${RED}✗ Coverage below 90% threshold: ${COVERAGE}%${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Coverage meets threshold: ${COVERAGE}%${NC}"
fi

echo ""
echo "======================================"
echo -e "${GREEN}✓ All tests passed!${NC}"
echo "======================================"
echo "Ready for deployment ✓"
echo ""

exit 0
