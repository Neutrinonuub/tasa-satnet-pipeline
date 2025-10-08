#!/usr/bin/env python3
"""Comprehensive tests for JSON schema validation.

Tests all schema validation functions for:
- OASIS windows (command, xband, TLE-derived)
- NS-3/SNS3 scenario configurations
- Metrics output formats

Run with: pytest tests/test_schemas.py -v
"""
from __future__ import annotations
import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.schemas import (
    validate_windows,
    validate_scenario,
    validate_metrics,
    validate_window_item,
    ValidationError,
    OASIS_WINDOW_SCHEMA,
    SCENARIO_SCHEMA,
    METRICS_SCHEMA,
)


# ============================================================================
# OASIS Windows Schema Tests
# ============================================================================

class TestWindowsSchema:
    """Test suite for OASIS windows schema validation."""

    def test_valid_window_passes(self):
        """Valid window data should pass validation."""
        valid_data = {
            "meta": {
                "source": "data/sample_oasis.log",
                "count": 2
            },
            "windows": [
                {
                    "type": "xband",
                    "start": "2025-10-08T02:00:00Z",
                    "end": "2025-10-08T02:08:00Z",
                    "sat": "SAT-1",
                    "gw": "TAIPEI",
                    "source": "log"
                },
                {
                    "type": "cmd",
                    "start": "2025-10-08T01:23:45Z",
                    "end": "2025-10-08T01:33:45Z",
                    "sat": "SAT-1",
                    "gw": "HSINCHU",
                    "source": "log"
                }
            ]
        }
        # Should not raise
        validate_windows(valid_data)

    def test_invalid_window_fails(self):
        """Invalid window data should fail validation."""
        invalid_data = {
            "meta": {"source": "test.log", "count": 1},
            "windows": [
                {
                    "type": "invalid_type",  # Invalid enum value
                    "start": "2025-10-08T02:00:00Z",
                    "end": "2025-10-08T02:08:00Z",
                    "sat": "SAT-1",
                    "gw": "TAIPEI",
                    "source": "log"
                }
            ]
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_windows(invalid_data)
        assert "validation failed" in str(exc_info.value).lower()

    def test_missing_required_field_fails(self):
        """Window missing required fields should fail."""
        invalid_data = {
            "meta": {"source": "test.log", "count": 1},
            "windows": [
                {
                    "type": "xband",
                    "start": "2025-10-08T02:00:00Z",
                    # Missing 'end', 'sat', 'gw', 'source'
                }
            ]
        }
        with pytest.raises(ValidationError):
            validate_windows(invalid_data)

    def test_schema_validates_time_format(self):
        """Schema should validate ISO 8601 time format."""
        # Valid ISO 8601 formats
        valid_times = [
            "2025-10-08T02:00:00Z",
            "2025-10-08T02:00:00+00:00",
            "2025-10-08T02:00:00-05:00",
        ]

        for time_str in valid_times:
            window = {
                "type": "xband",
                "start": time_str,
                "end": time_str,
                "sat": "SAT-1",
                "gw": "TAIPEI",
                "source": "log"
            }
            validate_window_item(window)  # Should not raise

        # Invalid time formats
        invalid_times = [
            "2025-10-08 02:00:00",  # Space instead of T
            "2025/10/08T02:00:00Z",  # Slashes instead of dashes
            "not-a-timestamp",
        ]

        for time_str in invalid_times:
            window = {
                "type": "xband",
                "start": time_str,
                "end": "2025-10-08T02:00:00Z",
                "sat": "SAT-1",
                "gw": "TAIPEI",
                "source": "log"
            }
            with pytest.raises(ValidationError):
                validate_window_item(window)

    def test_schema_validates_mode_enum(self):
        """Schema should validate window type enum values."""
        valid_types = ["cmd", "xband", "cmd_enter", "cmd_exit", "tle"]

        for window_type in valid_types:
            window = {
                "type": window_type,
                "start": "2025-10-08T02:00:00Z" if window_type not in ["cmd_exit"] else None,
                "end": "2025-10-08T02:08:00Z" if window_type not in ["cmd_enter"] else None,
                "sat": "SAT-1",
                "gw": "TAIPEI",
                "source": "log"
            }
            validate_window_item(window)  # Should not raise

        # Invalid type
        invalid_window = {
            "type": "invalid_type",
            "start": "2025-10-08T02:00:00Z",
            "end": "2025-10-08T02:08:00Z",
            "sat": "SAT-1",
            "gw": "TAIPEI",
            "source": "log"
        }
        with pytest.raises(ValidationError):
            validate_window_item(invalid_window)

    def test_window_with_elevation(self):
        """Window with elevation should validate correctly."""
        window = {
            "type": "tle",
            "start": "2025-10-08T02:00:00Z",
            "end": "2025-10-08T02:08:00Z",
            "sat": "SAT-1",
            "gw": "TAIPEI",
            "source": "tle",
            "elevation_deg": 45.5,
            "azimuth_deg": 180.0,
            "range_km": 550.0
        }
        validate_window_item(window)  # Should not raise

    def test_elevation_out_of_range(self):
        """Elevation outside 0-90 should fail."""
        window = {
            "type": "tle",
            "start": "2025-10-08T02:00:00Z",
            "end": "2025-10-08T02:08:00Z",
            "sat": "SAT-1",
            "gw": "TAIPEI",
            "source": "tle",
            "elevation_deg": 95.0  # Invalid: > 90
        }
        with pytest.raises(ValidationError):
            validate_window_item(window)

    def test_negative_count_fails(self):
        """Negative window count should fail."""
        invalid_data = {
            "meta": {"source": "test.log", "count": -1},
            "windows": []
        }
        with pytest.raises(ValidationError):
            validate_windows(invalid_data)


# ============================================================================
# Scenario Schema Tests
# ============================================================================

class TestScenarioSchema:
    """Test suite for NS-3/SNS3 scenario schema validation."""

    def test_valid_scenario_passes(self):
        """Valid scenario configuration should pass validation."""
        valid_scenario = {
            "metadata": {
                "name": "Test Scenario",
                "mode": "transparent",
                "generated_at": "2025-10-08T01:28:15.811290+00:00",
                "source": "data/sample_oasis.log"
            },
            "topology": {
                "satellites": [
                    {
                        "id": "SAT-1",
                        "type": "satellite",
                        "orbit": "LEO",
                        "altitude_km": 550
                    }
                ],
                "gateways": [
                    {
                        "id": "TAIPEI",
                        "type": "gateway",
                        "location": "TAIPEI",
                        "capacity_mbps": 100
                    }
                ],
                "links": [
                    {
                        "source": "SAT-1",
                        "target": "TAIPEI",
                        "type": "sat-ground",
                        "bandwidth_mbps": 50,
                        "latency_ms": 5.0
                    }
                ]
            },
            "events": [
                {
                    "time": "2025-10-08T02:00:00+00:00",
                    "type": "link_up",
                    "source": "SAT-1",
                    "target": "TAIPEI",
                    "window_type": "xband"
                }
            ],
            "parameters": {
                "relay_mode": "transparent",
                "propagation_model": "free_space",
                "data_rate_mbps": 50,
                "simulation_duration_sec": 86400,
                "processing_delay_ms": 0.0,
                "queuing_model": "fifo",
                "buffer_size_mb": 10
            }
        }
        validate_scenario(valid_scenario)  # Should not raise

    def test_invalid_relay_mode_fails(self):
        """Invalid relay mode should fail validation."""
        scenario = {
            "metadata": {
                "name": "Test",
                "mode": "invalid_mode",  # Invalid
                "generated_at": "2025-10-08T01:28:15+00:00"
            },
            "topology": {
                "satellites": [{"id": "SAT-1", "type": "satellite"}],
                "gateways": [{"id": "GW-1", "type": "gateway"}],
                "links": []
            },
            "events": [],
            "parameters": {
                "relay_mode": "transparent",
                "data_rate_mbps": 50
            }
        }
        with pytest.raises(ValidationError):
            validate_scenario(scenario)

    def test_missing_topology_fails(self):
        """Scenario missing topology should fail."""
        scenario = {
            "metadata": {
                "name": "Test",
                "mode": "transparent",
                "generated_at": "2025-10-08T01:28:15+00:00"
            },
            # Missing topology
            "events": [],
            "parameters": {
                "relay_mode": "transparent",
                "data_rate_mbps": 50
            }
        }
        with pytest.raises(ValidationError):
            validate_scenario(scenario)

    def test_empty_satellites_fails(self):
        """Topology with no satellites should fail."""
        scenario = {
            "metadata": {
                "name": "Test",
                "mode": "transparent",
                "generated_at": "2025-10-08T01:28:15+00:00"
            },
            "topology": {
                "satellites": [],  # Empty - invalid
                "gateways": [{"id": "GW-1", "type": "gateway"}],
                "links": []
            },
            "events": [],
            "parameters": {
                "relay_mode": "transparent",
                "data_rate_mbps": 50
            }
        }
        with pytest.raises(ValidationError):
            validate_scenario(scenario)

    def test_altitude_validation(self):
        """Satellite altitude should be validated."""
        # Valid altitude
        valid_sat = {
            "id": "SAT-1",
            "type": "satellite",
            "altitude_km": 550
        }

        scenario = {
            "metadata": {
                "name": "Test",
                "mode": "transparent",
                "generated_at": "2025-10-08T01:28:15+00:00"
            },
            "topology": {
                "satellites": [valid_sat],
                "gateways": [{"id": "GW-1", "type": "gateway"}],
                "links": []
            },
            "events": [],
            "parameters": {
                "relay_mode": "transparent",
                "data_rate_mbps": 50
            }
        }
        validate_scenario(scenario)  # Should pass

        # Invalid altitude (too low)
        invalid_sat = valid_sat.copy()
        invalid_sat["altitude_km"] = 100  # Below 160 km minimum

        scenario["topology"]["satellites"] = [invalid_sat]
        with pytest.raises(ValidationError):
            validate_scenario(scenario)

    def test_zero_data_rate_fails(self):
        """Data rate of zero should fail (exclusiveMinimum)."""
        scenario = {
            "metadata": {
                "name": "Test",
                "mode": "transparent",
                "generated_at": "2025-10-08T01:28:15+00:00"
            },
            "topology": {
                "satellites": [{"id": "SAT-1", "type": "satellite"}],
                "gateways": [{"id": "GW-1", "type": "gateway"}],
                "links": []
            },
            "events": [],
            "parameters": {
                "relay_mode": "transparent",
                "data_rate_mbps": 0  # Invalid: must be > 0
            }
        }
        with pytest.raises(ValidationError):
            validate_scenario(scenario)


# ============================================================================
# Metrics Schema Tests
# ============================================================================

class TestMetricsSchema:
    """Test suite for metrics output schema validation."""

    def test_valid_metrics_passes(self):
        """Valid metrics summary should pass validation."""
        valid_metrics = {
            "total_sessions": 2,
            "mode": "transparent",
            "latency": {
                "mean_ms": 7.34,
                "min_ms": 7.34,
                "max_ms": 7.34,
                "p95_ms": 7.34
            },
            "throughput": {
                "mean_mbps": 40.0,
                "min_mbps": 40.0,
                "max_mbps": 40.0
            },
            "total_duration_sec": 1080.0
        }
        validate_metrics(valid_metrics)  # Should not raise

    def test_missing_latency_field_fails(self):
        """Metrics missing required latency field should fail."""
        invalid_metrics = {
            "total_sessions": 2,
            "mode": "transparent",
            # Missing latency
            "throughput": {
                "mean_mbps": 40.0,
                "min_mbps": 40.0,
                "max_mbps": 40.0
            }
        }
        with pytest.raises(ValidationError):
            validate_metrics(invalid_metrics)

    def test_negative_latency_fails(self):
        """Negative latency values should fail."""
        invalid_metrics = {
            "total_sessions": 2,
            "mode": "transparent",
            "latency": {
                "mean_ms": -5.0,  # Invalid: negative
                "min_ms": 7.34,
                "max_ms": 7.34,
                "p95_ms": 7.34
            },
            "throughput": {
                "mean_mbps": 40.0,
                "min_mbps": 40.0,
                "max_mbps": 40.0
            }
        }
        with pytest.raises(ValidationError):
            validate_metrics(invalid_metrics)

    def test_invalid_mode_fails(self):
        """Invalid mode should fail validation."""
        invalid_metrics = {
            "total_sessions": 2,
            "mode": "invalid_mode",  # Invalid
            "latency": {
                "mean_ms": 7.34,
                "min_ms": 7.34,
                "max_ms": 7.34,
                "p95_ms": 7.34
            },
            "throughput": {
                "mean_mbps": 40.0,
                "min_mbps": 40.0,
                "max_mbps": 40.0
            }
        }
        with pytest.raises(ValidationError):
            validate_metrics(invalid_metrics)

    def test_zero_sessions_valid(self):
        """Zero sessions should be valid."""
        valid_metrics = {
            "total_sessions": 0,
            "mode": "transparent",
            "latency": {
                "mean_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "p95_ms": 0.0
            },
            "throughput": {
                "mean_mbps": 0.0,
                "min_mbps": 0.0,
                "max_mbps": 0.0
            }
        }
        validate_metrics(valid_metrics)  # Should not raise


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_window_with_null_times(self):
        """cmd_enter/exit windows can have null start/end."""
        # cmd_enter can have null end
        enter_window = {
            "type": "cmd_enter",
            "start": "2025-10-08T01:23:45Z",
            "end": None,
            "sat": "SAT-1",
            "gw": "HSINCHU",
            "source": "log"
        }
        validate_window_item(enter_window)  # Should not raise

        # cmd_exit can have null start
        exit_window = {
            "type": "cmd_exit",
            "start": None,
            "end": "2025-10-08T01:33:45Z",
            "sat": "SAT-1",
            "gw": "HSINCHU",
            "source": "log"
        }
        validate_window_item(exit_window)  # Should not raise

    def test_complete_pipeline_validation(self):
        """Test validation across entire pipeline."""
        # Step 1: Valid windows
        windows = {
            "meta": {"source": "test.log", "count": 1},
            "windows": [
                {
                    "type": "xband",
                    "start": "2025-10-08T02:00:00Z",
                    "end": "2025-10-08T02:08:00Z",
                    "sat": "SAT-1",
                    "gw": "TAIPEI",
                    "source": "log"
                }
            ]
        }
        validate_windows(windows)

        # Step 2: Valid scenario
        scenario = {
            "metadata": {
                "name": "Pipeline Test",
                "mode": "regenerative",
                "generated_at": datetime.now(timezone.utc).isoformat()
            },
            "topology": {
                "satellites": [{"id": "SAT-1", "type": "satellite"}],
                "gateways": [{"id": "TAIPEI", "type": "gateway"}],
                "links": [
                    {
                        "source": "SAT-1",
                        "target": "TAIPEI",
                        "type": "sat-ground"
                    }
                ]
            },
            "events": [
                {
                    "time": "2025-10-08T02:00:00+00:00",
                    "type": "link_up",
                    "source": "SAT-1",
                    "target": "TAIPEI"
                }
            ],
            "parameters": {
                "relay_mode": "regenerative",
                "data_rate_mbps": 50
            }
        }
        validate_scenario(scenario)

        # Step 3: Valid metrics
        metrics = {
            "total_sessions": 1,
            "mode": "regenerative",
            "latency": {
                "mean_ms": 12.34,
                "min_ms": 12.34,
                "max_ms": 12.34,
                "p95_ms": 12.34
            },
            "throughput": {
                "mean_mbps": 40.0,
                "min_mbps": 40.0,
                "max_mbps": 40.0
            }
        }
        validate_metrics(metrics)

    def test_multiple_satellites_and_gateways(self):
        """Test scenario with multiple nodes."""
        scenario = {
            "metadata": {
                "name": "Multi-node Test",
                "mode": "transparent",
                "generated_at": "2025-10-08T01:28:15+00:00"
            },
            "topology": {
                "satellites": [
                    {"id": "SAT-1", "type": "satellite", "altitude_km": 550},
                    {"id": "SAT-2", "type": "satellite", "altitude_km": 600},
                    {"id": "SAT-3", "type": "satellite", "altitude_km": 575}
                ],
                "gateways": [
                    {"id": "TAIPEI", "type": "gateway", "latitude": 25.0, "longitude": 121.5},
                    {"id": "HSINCHU", "type": "gateway", "latitude": 24.8, "longitude": 120.9}
                ],
                "links": [
                    {"source": "SAT-1", "target": "TAIPEI", "type": "sat-ground"},
                    {"source": "SAT-2", "target": "HSINCHU", "type": "sat-ground"},
                    {"source": "SAT-1", "target": "SAT-2", "type": "sat-sat"}
                ]
            },
            "events": [],
            "parameters": {
                "relay_mode": "transparent",
                "data_rate_mbps": 100
            }
        }
        validate_scenario(scenario)  # Should not raise


class TestMainBlock:
    """Test the __main__ block execution."""

    def test_main_execution_via_import(self, capsys, monkeypatch):
        """Test that __main__ block logic executes without errors."""
        # Simulate __main__ execution by directly calling the logic
        from config.schemas import (
            get_schema_version,
            list_required_fields,
            get_enum_values,
            OASIS_WINDOW_SCHEMA,
            SCENARIO_SCHEMA,
            METRICS_SCHEMA
        )

        # Execute the same logic as in __main__
        print("OASIS Window Schema:")
        print(f"  Version: {get_schema_version(OASIS_WINDOW_SCHEMA)}")
        print(f"  Required fields: {list_required_fields(OASIS_WINDOW_SCHEMA)}")
        print(f"  Window types: {get_enum_values(OASIS_WINDOW_SCHEMA, 'windows.items.type')}")

        print("\nScenario Schema:")
        print(f"  Version: {get_schema_version(SCENARIO_SCHEMA)}")
        print(f"  Required fields: {list_required_fields(SCENARIO_SCHEMA)}")
        print(f"  Relay modes: {get_enum_values(SCENARIO_SCHEMA, 'metadata.mode')}")

        print("\nMetrics Schema:")
        print(f"  Version: {get_schema_version(METRICS_SCHEMA)}")
        print(f"  Required fields: {list_required_fields(METRICS_SCHEMA)}")
        print(f"  Modes: {get_enum_values(METRICS_SCHEMA, 'mode')}")

        # Verify output was generated
        captured = capsys.readouterr()
        assert "OASIS Window Schema:" in captured.out
        assert "Scenario Schema:" in captured.out
        assert "Metrics Schema:" in captured.out
        assert "Version:" in captured.out
        assert "Required fields:" in captured.out

    def test_main_execution_subprocess(self, capsys):
        """Test that __main__ block executes as a script without errors."""
        import subprocess
        import sys

        # Run the schemas.py file as a script
        result = subprocess.run(
            [sys.executable, "config/schemas.py"],
            cwd="C:\\Users\\thc1006\\Downloads\\open-source\\tasa-satnet-pipeline",
            capture_output=True,
            text=True
        )

        # Should execute successfully
        assert result.returncode == 0

        # Should output schema information
        output = result.stdout
        assert "OASIS Window Schema:" in output
        assert "Scenario Schema:" in output
        assert "Metrics Schema:" in output
        assert "Version:" in output
        assert "Required fields:" in output


class TestUtilityFunctions:
    """Test suite for schema utility functions."""

    def test_get_schema_version(self):
        """get_schema_version should extract schema version."""
        from config.schemas import get_schema_version, OASIS_WINDOW_SCHEMA, SCENARIO_SCHEMA

        version = get_schema_version(OASIS_WINDOW_SCHEMA)
        assert version == "http://json-schema.org/draft-07/schema#"

        version = get_schema_version(SCENARIO_SCHEMA)
        assert version == "http://json-schema.org/draft-07/schema#"

        # Schema without version
        version = get_schema_version({"type": "object"})
        assert version == "unknown"

    def test_list_required_fields(self):
        """list_required_fields should extract required fields."""
        from config.schemas import list_required_fields, OASIS_WINDOW_SCHEMA, SCENARIO_SCHEMA

        required = list_required_fields(OASIS_WINDOW_SCHEMA)
        assert "meta" in required
        assert "windows" in required

        required = list_required_fields(SCENARIO_SCHEMA)
        assert "metadata" in required
        assert "topology" in required
        assert "events" in required
        assert "parameters" in required

        # Schema without required fields
        required = list_required_fields({"type": "object"})
        assert required == []

    def test_get_enum_values_simple_path(self):
        """get_enum_values should extract enum values for simple paths."""
        from config.schemas import get_enum_values, SCENARIO_SCHEMA, METRICS_SCHEMA

        # Test metadata.mode
        modes = get_enum_values(SCENARIO_SCHEMA, "metadata.mode")
        assert "transparent" in modes
        assert "regenerative" in modes

        # Test parameters.relay_mode
        relay_modes = get_enum_values(SCENARIO_SCHEMA, "parameters.relay_mode")
        assert "transparent" in relay_modes
        assert "regenerative" in relay_modes

        # Test metrics mode
        metrics_modes = get_enum_values(METRICS_SCHEMA, "mode")
        assert "transparent" in metrics_modes
        assert "regenerative" in metrics_modes

    def test_get_enum_values_propagation_model(self):
        """get_enum_values should extract propagation model enums."""
        from config.schemas import get_enum_values, SCENARIO_SCHEMA

        models = get_enum_values(SCENARIO_SCHEMA, "parameters.propagation_model")
        assert "free_space" in models
        assert "two_ray_ground" in models
        assert "log_distance" in models

    def test_get_enum_values_queuing_model(self):
        """get_enum_values should extract queuing model enums."""
        from config.schemas import get_enum_values, SCENARIO_SCHEMA

        models = get_enum_values(SCENARIO_SCHEMA, "parameters.queuing_model")
        assert "fifo" in models
        assert "priority" in models
        assert "weighted_fair" in models

    def test_get_enum_values_nonexistent_path(self):
        """get_enum_values should return empty list for invalid paths."""
        from config.schemas import get_enum_values, SCENARIO_SCHEMA

        # Nonexistent path
        result = get_enum_values(SCENARIO_SCHEMA, "nonexistent.field.path")
        assert result == []

        # Path to non-enum field
        result = get_enum_values(SCENARIO_SCHEMA, "metadata.name")
        assert result == []

    def test_get_enum_values_nested_definitions(self):
        """get_enum_values should handle deeply nested paths."""
        from config.schemas import get_enum_values, OASIS_WINDOW_SCHEMA

        # This tests the complex path navigation logic
        # Even though we can't easily get to definitions, test boundary cases
        result = get_enum_values(OASIS_WINDOW_SCHEMA, "meta.source")
        assert result == []  # Not an enum field

    def test_get_enum_values_with_nested_properties(self):
        """Test get_enum_values with various nested property paths."""
        from config.schemas import get_enum_values, SCENARIO_SCHEMA

        # Test deeply nested path
        result = get_enum_values(SCENARIO_SCHEMA, "parameters.propagation_model")
        assert len(result) == 3

        # Test path that doesn't have 'properties' key at some level
        result = get_enum_values(SCENARIO_SCHEMA, "topology.satellites.orbit")
        assert result == []  # Can't navigate through arrays in this implementation

    def test_get_enum_values_empty_path(self):
        """Test get_enum_values with edge case paths."""
        from config.schemas import get_enum_values, SCENARIO_SCHEMA

        # Empty string path
        result = get_enum_values(SCENARIO_SCHEMA, "")
        assert result == []

        # Single component path
        result = get_enum_values(SCENARIO_SCHEMA, "metadata")
        assert result == []  # Not an enum, it's an object

    def test_all_window_source_enums(self):
        """Test window source enum values are accessible."""
        from config.schemas import OASIS_WINDOW_SCHEMA

        # Manually check the window source enum in definitions
        window_def = OASIS_WINDOW_SCHEMA["definitions"]["window"]
        source_prop = window_def["properties"]["source"]
        assert "enum" in source_prop
        assert "log" in source_prop["enum"]
        assert "tle" in source_prop["enum"]

    def test_all_window_type_enums(self):
        """Test all window type enum values."""
        from config.schemas import OASIS_WINDOW_SCHEMA

        # Check window type enum
        window_def = OASIS_WINDOW_SCHEMA["definitions"]["window"]
        type_prop = window_def["properties"]["type"]
        assert "enum" in type_prop
        expected_types = ["cmd", "xband", "cmd_enter", "cmd_exit", "tle"]
        for wtype in expected_types:
            assert wtype in type_prop["enum"]


class TestErrorHandlingPaths:
    """Test suite for error handling edge cases."""

    def test_schema_error_in_validate_windows(self):
        """validate_windows should handle SchemaError gracefully."""
        import jsonschema
        from config.schemas import validate_windows, ValidationError

        # Create invalid schema by modifying OASIS_WINDOW_SCHEMA temporarily
        # This is tricky - we need to trigger SchemaError
        # One way is to pass malformed data that causes schema evaluation issues

        # Instead, test that the error path exists by mocking
        import unittest.mock as mock

        with mock.patch('jsonschema.validate', side_effect=jsonschema.SchemaError("Invalid schema")):
            with pytest.raises(ValidationError) as exc_info:
                validate_windows({"meta": {"source": "test", "count": 0}, "windows": []})
            assert "Invalid schema definition" in str(exc_info.value)

    def test_schema_error_in_validate_scenario(self):
        """validate_scenario should handle SchemaError gracefully."""
        import jsonschema
        from config.schemas import validate_scenario, ValidationError
        import unittest.mock as mock

        with mock.patch('jsonschema.validate', side_effect=jsonschema.SchemaError("Invalid schema")):
            with pytest.raises(ValidationError) as exc_info:
                validate_scenario({
                    "metadata": {"name": "test", "mode": "transparent", "generated_at": "2025-10-08T00:00:00Z"},
                    "topology": {"satellites": [{"id": "s1", "type": "satellite"}], "gateways": [{"id": "g1", "type": "gateway"}], "links": []},
                    "events": [],
                    "parameters": {"relay_mode": "transparent", "data_rate_mbps": 50}
                })
            assert "Invalid schema definition" in str(exc_info.value)

    def test_schema_error_in_validate_metrics(self):
        """validate_metrics should handle SchemaError gracefully."""
        import jsonschema
        from config.schemas import validate_metrics, ValidationError
        import unittest.mock as mock

        with mock.patch('jsonschema.validate', side_effect=jsonschema.SchemaError("Invalid schema")):
            with pytest.raises(ValidationError) as exc_info:
                validate_metrics({
                    "total_sessions": 0,
                    "mode": "transparent",
                    "latency": {"mean_ms": 0, "min_ms": 0, "max_ms": 0, "p95_ms": 0},
                    "throughput": {"mean_mbps": 0, "min_mbps": 0, "max_mbps": 0}
                })
            assert "Invalid schema definition" in str(exc_info.value)

    def test_validation_error_with_nested_path(self):
        """ValidationError should include full path information."""
        from config.schemas import validate_windows, ValidationError

        # Create data with nested error
        invalid_data = {
            "meta": {"source": "test.log", "count": 1},
            "windows": [
                {
                    "type": "xband",
                    "start": "2025-10-08T02:00:00Z",
                    "end": "2025-10-08T02:08:00Z",
                    "sat": "",  # Invalid: minLength is 1
                    "gw": "TAIPEI",
                    "source": "log"
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_windows(invalid_data)

        error_msg = str(exc_info.value)
        assert "validation failed" in error_msg.lower()
        # Should include path information
        assert "Path:" in error_msg or "path" in error_msg.lower()

    def test_validation_error_multiple_issues(self):
        """ValidationError should report first validation issue."""
        from config.schemas import validate_scenario, ValidationError

        # Scenario with multiple errors
        invalid_scenario = {
            "metadata": {
                "name": "",  # Invalid: minLength is 1
                "mode": "invalid",  # Invalid: not in enum
                "generated_at": "not-a-date"  # Invalid: not date-time format
            },
            "topology": {
                "satellites": [],  # Invalid: minItems is 1
                "gateways": [],  # Invalid: minItems is 1
                "links": []
            },
            "events": [],
            "parameters": {
                "relay_mode": "transparent",
                "data_rate_mbps": -1  # Invalid: must be > 0
            }
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_scenario(invalid_scenario)

        # Should catch first error and provide informative message
        assert "validation failed" in str(exc_info.value).lower()


class TestComplexValidationScenarios:
    """Test complex validation scenarios and boundary conditions."""

    def test_empty_windows_array_valid(self):
        """Empty windows array should be valid if count is 0."""
        from config.schemas import validate_windows

        valid_data = {
            "meta": {"source": "test.log", "count": 0},
            "windows": []
        }
        validate_windows(valid_data)  # Should not raise

    def test_window_with_all_optional_fields(self):
        """Window with all optional fields populated."""
        from config.schemas import validate_window_item

        complete_window = {
            "type": "tle",
            "start": "2025-10-08T02:00:00Z",
            "end": "2025-10-08T02:08:00Z",
            "sat": "SAT-1",
            "gw": "TAIPEI",
            "source": "tle",
            "elevation_deg": 45.5,
            "azimuth_deg": 180.0,
            "range_km": 550.0
        }
        validate_window_item(complete_window)  # Should not raise

    def test_azimuth_boundary_values(self):
        """Test azimuth angle boundary values."""
        from config.schemas import validate_window_item

        # Test 0 degrees
        window = {
            "type": "tle",
            "start": "2025-10-08T02:00:00Z",
            "end": "2025-10-08T02:08:00Z",
            "sat": "SAT-1",
            "gw": "TAIPEI",
            "source": "tle",
            "azimuth_deg": 0.0
        }
        validate_window_item(window)  # Should pass

        # Test 360 degrees
        window["azimuth_deg"] = 360.0
        validate_window_item(window)  # Should pass

        # Test > 360 (should fail)
        window["azimuth_deg"] = 361.0
        with pytest.raises(ValidationError):
            validate_window_item(window)

    def test_range_km_boundary_values(self):
        """Test range_km validation."""
        from config.schemas import validate_window_item

        # Valid: 0 km
        window = {
            "type": "tle",
            "start": "2025-10-08T02:00:00Z",
            "end": "2025-10-08T02:08:00Z",
            "sat": "SAT-1",
            "gw": "TAIPEI",
            "source": "tle",
            "range_km": 0.0
        }
        validate_window_item(window)  # Should pass

        # Valid: very large range
        window["range_km"] = 50000.0
        validate_window_item(window)  # Should pass

        # Invalid: negative range
        window["range_km"] = -100.0
        with pytest.raises(ValidationError):
            validate_window_item(window)

    def test_satellite_orbit_types(self):
        """Test all satellite orbit types."""
        from config.schemas import validate_scenario

        orbit_types = ["LEO", "MEO", "GEO", "HEO"]

        for orbit in orbit_types:
            scenario = {
                "metadata": {
                    "name": f"Test {orbit}",
                    "mode": "transparent",
                    "generated_at": "2025-10-08T01:28:15+00:00"
                },
                "topology": {
                    "satellites": [{
                        "id": "SAT-1",
                        "type": "satellite",
                        "orbit": orbit,
                        "altitude_km": 550 if orbit == "LEO" else 20000
                    }],
                    "gateways": [{"id": "GW-1", "type": "gateway"}],
                    "links": []
                },
                "events": [],
                "parameters": {
                    "relay_mode": "transparent",
                    "data_rate_mbps": 50
                }
            }
            validate_scenario(scenario)  # Should not raise

    def test_gateway_types(self):
        """Test all gateway types."""
        from config.schemas import validate_scenario

        gateway_types = ["gateway", "ground_station", "terminal"]

        for gw_type in gateway_types:
            scenario = {
                "metadata": {
                    "name": f"Test {gw_type}",
                    "mode": "transparent",
                    "generated_at": "2025-10-08T01:28:15+00:00"
                },
                "topology": {
                    "satellites": [{"id": "SAT-1", "type": "satellite"}],
                    "gateways": [{
                        "id": "GW-1",
                        "type": gw_type,
                        "latitude": 25.0,
                        "longitude": 121.5
                    }],
                    "links": []
                },
                "events": [],
                "parameters": {
                    "relay_mode": "transparent",
                    "data_rate_mbps": 50
                }
            }
            validate_scenario(scenario)  # Should not raise

    def test_link_types(self):
        """Test all link types."""
        from config.schemas import validate_scenario

        link_configs = [
            ("sat-ground", "SAT-1", "GW-1"),
            ("sat-sat", "SAT-1", "SAT-2"),
            ("ground-ground", "GW-1", "GW-2")
        ]

        for link_type, source, target in link_configs:
            # Create appropriate topology
            satellites = [{"id": "SAT-1", "type": "satellite"}]
            gateways = [{"id": "GW-1", "type": "gateway"}]

            if "SAT-2" in [source, target]:
                satellites.append({"id": "SAT-2", "type": "satellite"})
            if "GW-2" in [source, target]:
                gateways.append({"id": "GW-2", "type": "gateway"})

            scenario = {
                "metadata": {
                    "name": f"Test {link_type}",
                    "mode": "transparent",
                    "generated_at": "2025-10-08T01:28:15+00:00"
                },
                "topology": {
                    "satellites": satellites,
                    "gateways": gateways,
                    "links": [{
                        "source": source,
                        "target": target,
                        "type": link_type,
                        "bandwidth_mbps": 100,
                        "latency_ms": 5.0
                    }]
                },
                "events": [],
                "parameters": {
                    "relay_mode": "transparent",
                    "data_rate_mbps": 50
                }
            }
            validate_scenario(scenario)  # Should not raise

    def test_event_types(self):
        """Test all event types."""
        from config.schemas import validate_scenario

        event_types = ["link_up", "link_down", "handover", "failure", "recovery"]

        for event_type in event_types:
            scenario = {
                "metadata": {
                    "name": f"Test {event_type}",
                    "mode": "transparent",
                    "generated_at": "2025-10-08T01:28:15+00:00"
                },
                "topology": {
                    "satellites": [{"id": "SAT-1", "type": "satellite"}],
                    "gateways": [{"id": "GW-1", "type": "gateway"}],
                    "links": []
                },
                "events": [{
                    "time": "2025-10-08T02:00:00+00:00",
                    "type": event_type,
                    "source": "SAT-1",
                    "target": "GW-1",
                    "window_type": "xband"
                }],
                "parameters": {
                    "relay_mode": "transparent",
                    "data_rate_mbps": 50
                }
            }
            validate_scenario(scenario)  # Should not raise

    def test_latitude_longitude_boundaries(self):
        """Test latitude and longitude boundary values."""
        from config.schemas import validate_scenario

        # Valid boundaries
        valid_coords = [
            (90, 180),    # North pole, max east
            (-90, -180),  # South pole, max west
            (0, 0),       # Equator, prime meridian
            (45.5, 121.5) # Normal coordinates
        ]

        for lat, lon in valid_coords:
            scenario = {
                "metadata": {
                    "name": "Test coords",
                    "mode": "transparent",
                    "generated_at": "2025-10-08T01:28:15+00:00"
                },
                "topology": {
                    "satellites": [{"id": "SAT-1", "type": "satellite"}],
                    "gateways": [{
                        "id": "GW-1",
                        "type": "gateway",
                        "latitude": lat,
                        "longitude": lon
                    }],
                    "links": []
                },
                "events": [],
                "parameters": {
                    "relay_mode": "transparent",
                    "data_rate_mbps": 50
                }
            }
            validate_scenario(scenario)  # Should not raise

        # Invalid: latitude > 90
        scenario["topology"]["gateways"][0]["latitude"] = 91
        with pytest.raises(ValidationError):
            validate_scenario(scenario)

    def test_altitude_boundaries(self):
        """Test satellite altitude boundary validation."""
        from config.schemas import validate_scenario

        # Valid: minimum LEO altitude (160 km)
        scenario = {
            "metadata": {
                "name": "Test altitude",
                "mode": "transparent",
                "generated_at": "2025-10-08T01:28:15+00:00"
            },
            "topology": {
                "satellites": [{
                    "id": "SAT-1",
                    "type": "satellite",
                    "altitude_km": 160
                }],
                "gateways": [{"id": "GW-1", "type": "gateway"}],
                "links": []
            },
            "events": [],
            "parameters": {
                "relay_mode": "transparent",
                "data_rate_mbps": 50
            }
        }
        validate_scenario(scenario)  # Should pass

        # Valid: maximum altitude (50000 km)
        scenario["topology"]["satellites"][0]["altitude_km"] = 50000
        validate_scenario(scenario)  # Should pass

        # Invalid: too high
        scenario["topology"]["satellites"][0]["altitude_km"] = 50001
        with pytest.raises(ValidationError):
            validate_scenario(scenario)

    def test_inclination_boundaries(self):
        """Test satellite inclination boundary values."""
        from config.schemas import validate_scenario

        for inclination in [0, 90, 180]:
            scenario = {
                "metadata": {
                    "name": f"Test inclination {inclination}",
                    "mode": "transparent",
                    "generated_at": "2025-10-08T01:28:15+00:00"
                },
                "topology": {
                    "satellites": [{
                        "id": "SAT-1",
                        "type": "satellite",
                        "inclination_deg": inclination
                    }],
                    "gateways": [{"id": "GW-1", "type": "gateway"}],
                    "links": []
                },
                "events": [],
                "parameters": {
                    "relay_mode": "transparent",
                    "data_rate_mbps": 50
                }
            }
            validate_scenario(scenario)  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
