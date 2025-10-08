# Test runner script for Windows (PowerShell)
# TDD: Tests must pass before deployment

param(
    [switch]$RunBenchmarks = $false
)

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "TASA SatNet Pipeline - Test Runner" -ForegroundColor Cyan
Write-Host "TDD: Tests must pass before deployment" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if venv exists
if (-not (Test-Path "venv")) {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install --upgrade pip
    pip install -r requirements.txt
} else {
    .\venv\Scripts\Activate.ps1
}

Write-Host "Python version: $(python --version)"
Write-Host "Pytest version: $(pytest --version)"
Write-Host ""

# Run linting first
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Step 1: Code Linting" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
if (Get-Command flake8 -ErrorAction SilentlyContinue) {
    Write-Host "Running flake8..."
    flake8 scripts\ tests\ --max-line-length=100 --statistics
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Linting failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Linting passed" -ForegroundColor Green
} else {
    Write-Host "⚠ flake8 not installed, skipping linting" -ForegroundColor Yellow
}
Write-Host ""

# Run type checking
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Step 2: Type Checking" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
if (Get-Command mypy -ErrorAction SilentlyContinue) {
    Write-Host "Running mypy..."
    mypy scripts\ --ignore-missing-imports
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Type checking failed (non-blocking)" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠ mypy not installed, skipping type checking" -ForegroundColor Yellow
}
Write-Host ""

# Run unit tests
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Step 3: Unit Tests" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
pytest tests\ -v `
    -m "not slow and not integration and not docker and not k8s" `
    --cov=scripts `
    --cov-report=term-missing `
    --cov-report=html `
    --cov-report=xml `
    --cov-fail-under=90

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Unit tests failed!" -ForegroundColor Red
    Write-Host "Tests must pass before deployment (TDD principle)" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Unit tests passed" -ForegroundColor Green
Write-Host ""

# Run integration tests (if available)
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Step 4: Integration Tests" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
$hasIntegrationTests = (pytest tests\ -m "integration" --collect-only 2>&1 | Select-String -Pattern "test" -Quiet)
if ($hasIntegrationTests) {
    pytest tests\ -v -m "integration"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Integration tests failed (non-blocking)" -ForegroundColor Yellow
    }
} else {
    Write-Host "No integration tests found, skipping..."
}
Write-Host ""

# Run benchmark tests (if requested)
if ($RunBenchmarks) {
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Step 5: Benchmark Tests" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    pytest tests\ -m "benchmark" --benchmark-only
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Benchmark tests failed (non-blocking)" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Generate coverage report
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Test Coverage Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
coverage report --show-missing
Write-Host ""
Write-Host "Detailed HTML coverage report: htmlcov\index.html"
Write-Host ""

# Check coverage threshold
$coverageOutput = coverage report | Select-String "TOTAL" | Out-String
$coverage = [regex]::Match($coverageOutput, '(\d+)%').Groups[1].Value
if ([int]$coverage -lt 90) {
    Write-Host "✗ Coverage below 90% threshold: ${coverage}%" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✓ Coverage meets threshold: ${coverage}%" -ForegroundColor Green
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "✓ All tests passed!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Ready for deployment ✓" -ForegroundColor Green
Write-Host ""

exit 0
