#!/usr/bin/env python3
"""Deployment and integration tests."""
import pytest
import json
import subprocess
from pathlib import Path


@pytest.mark.integration
def test_full_pipeline_local():
    """Test complete pipeline runs locally."""
    # Parse
    result = subprocess.run([
        "python", "scripts/parse_oasis_log.py",
        "data/sample_oasis.log",
        "-o", "data/test_pipeline.json"
    ], capture_output=True, text=True)
    assert result.returncode == 0, f"Parser failed: {result.stderr}"
    
    # Scenario
    result = subprocess.run([
        "python", "scripts/gen_scenario.py",
        "data/test_pipeline.json",
        "-o", "config/test_scenario.json"
    ], capture_output=True, text=True)
    assert result.returncode == 0, f"Scenario failed: {result.stderr}"
    
    # Metrics
    result = subprocess.run([
        "python", "scripts/metrics.py",
        "config/test_scenario.json",
        "-o", "reports/test_metrics.csv"
    ], capture_output=True, text=True)
    assert result.returncode == 0, f"Metrics failed: {result.stderr}"
    
    # Scheduler
    result = subprocess.run([
        "python", "scripts/scheduler.py",
        "config/test_scenario.json",
        "-o", "reports/test_schedule.csv"
    ], capture_output=True, text=True)
    assert result.returncode == 0, f"Scheduler failed: {result.stderr}"


@pytest.mark.docker
def test_docker_build():
    """Test Docker image builds successfully."""
    result = subprocess.run([
        "docker", "build", "-t", "tasa-satnet-pipeline:test", "."
    ], capture_output=True, text=True)
    assert result.returncode == 0, f"Docker build failed: {result.stderr}"


@pytest.mark.docker
def test_docker_healthcheck():
    """Test Docker container health check."""
    # Build image
    subprocess.run(["docker", "build", "-t", "tasa-satnet-pipeline:test", "."])
    
    # Run health check
    result = subprocess.run([
        "docker", "run", "--rm",
        "tasa-satnet-pipeline:test",
        "python", "scripts/healthcheck.py"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"Health check failed: {result.stderr}"
    assert "OK" in result.stdout


@pytest.mark.k8s
def test_k8s_deployment():
    """Test K8s deployment can be created."""
    # Check if kubectl is available
    result = subprocess.run(["kubectl", "version", "--client"],
                          capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip("kubectl not available")
    
    # Try to get cluster info
    result = subprocess.run(["kubectl", "cluster-info"],
                          capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip("K8s cluster not accessible")
    
    # Apply namespace
    result = subprocess.run([
        "kubectl", "apply", "-f", "k8s/namespace.yaml"
    ], capture_output=True, text=True)
    assert result.returncode == 0, f"Namespace creation failed: {result.stderr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
