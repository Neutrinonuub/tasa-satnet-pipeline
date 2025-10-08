#!/usr/bin/env python3
"""JSON Schema definitions and validation functions for TASA SatNet Pipeline.

This module provides comprehensive schema validation for:
- OASIS log windows (command, xband, TLE-derived)
- NS-3/SNS3 scenario configurations
- Metrics output formats

Usage:
    from config.schemas import validate_windows, validate_scenario, validate_metrics

    # Validate parsed OASIS windows
    validate_windows(windows_data)

    # Validate scenario configuration
    validate_scenario(scenario_data)

    # Validate metrics output
    validate_metrics(metrics_data)
"""
from __future__ import annotations
import jsonschema
from typing import Dict, List, Any


# ============================================================================
# OASIS Windows Schema
# ============================================================================

OASIS_WINDOW_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "OASIS Windows Data",
    "description": "Parsed satellite communication windows from OASIS logs",
    "type": "object",
    "required": ["meta", "windows"],
    "properties": {
        "meta": {
            "type": "object",
            "required": ["source", "count"],
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source log file path"
                },
                "count": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of windows extracted"
                }
            }
        },
        "windows": {
            "type": "array",
            "items": {
                "$ref": "#/definitions/window"
            }
        }
    },
    "definitions": {
        "window": {
            "type": "object",
            "required": ["type", "sat", "gw", "source"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["cmd", "xband", "cmd_enter", "cmd_exit", "tle"],
                    "description": "Window type: cmd (command), xband (X-band data link), tle (TLE-derived)"
                },
                "start": {
                    "type": ["string", "null"],
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(Z|[+-]\\d{2}:\\d{2})$",
                    "description": "Start time in ISO 8601 format"
                },
                "end": {
                    "type": ["string", "null"],
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(Z|[+-]\\d{2}:\\d{2})$",
                    "description": "End time in ISO 8601 format"
                },
                "sat": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Satellite identifier"
                },
                "gw": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Gateway/ground station identifier"
                },
                "source": {
                    "type": "string",
                    "enum": ["log", "tle"],
                    "description": "Data source: log (OASIS log) or tle (TLE calculation)"
                },
                "elevation_deg": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 90,
                    "description": "Maximum elevation angle in degrees (for TLE-derived windows)"
                },
                "azimuth_deg": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 360,
                    "description": "Azimuth angle in degrees"
                },
                "range_km": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Range to satellite in kilometers"
                }
            },
            "allOf": [
                {
                    "if": {
                        "properties": {
                            "type": {"enum": ["cmd", "xband", "tle"]}
                        }
                    },
                    "then": {
                        "required": ["start", "end"]
                    }
                }
            ]
        }
    }
}


# ============================================================================
# NS-3/SNS3 Scenario Schema
# ============================================================================

SCENARIO_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NS-3/SNS3 Scenario Configuration",
    "description": "Network simulation scenario with satellites, gateways, and events",
    "type": "object",
    "required": ["metadata", "topology", "events", "parameters"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["name", "mode", "generated_at"],
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1
                },
                "mode": {
                    "type": "string",
                    "enum": ["transparent", "regenerative"],
                    "description": "Relay mode: transparent (bent-pipe) or regenerative (processing)"
                },
                "generated_at": {
                    "type": "string",
                    "format": "date-time"
                },
                "source": {
                    "type": "string"
                }
            }
        },
        "topology": {
            "type": "object",
            "required": ["satellites", "gateways", "links"],
            "properties": {
                "satellites": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "$ref": "#/definitions/satellite"
                    }
                },
                "gateways": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "$ref": "#/definitions/gateway"
                    }
                },
                "links": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/link"
                    }
                }
            }
        },
        "events": {
            "type": "array",
            "items": {
                "$ref": "#/definitions/event"
            }
        },
        "parameters": {
            "type": "object",
            "required": ["relay_mode", "data_rate_mbps"],
            "properties": {
                "relay_mode": {
                    "type": "string",
                    "enum": ["transparent", "regenerative"]
                },
                "propagation_model": {
                    "type": "string",
                    "enum": ["free_space", "two_ray_ground", "log_distance"]
                },
                "data_rate_mbps": {
                    "type": "number",
                    "exclusiveMinimum": 0
                },
                "simulation_duration_sec": {
                    "type": "number",
                    "minimum": 0
                },
                "processing_delay_ms": {
                    "type": "number",
                    "minimum": 0
                },
                "queuing_model": {
                    "type": "string",
                    "enum": ["fifo", "priority", "weighted_fair"]
                },
                "buffer_size_mb": {
                    "type": "number",
                    "minimum": 0
                }
            }
        }
    },
    "definitions": {
        "satellite": {
            "type": "object",
            "required": ["id", "type"],
            "properties": {
                "id": {
                    "type": "string",
                    "minLength": 1
                },
                "type": {
                    "type": "string",
                    "enum": ["satellite"]
                },
                "orbit": {
                    "type": "string",
                    "enum": ["LEO", "MEO", "GEO", "HEO"]
                },
                "altitude_km": {
                    "type": "number",
                    "minimum": 160,
                    "maximum": 50000,
                    "description": "Altitude in kilometers (160 km min for LEO, up to 50000 km for GEO)"
                },
                "inclination_deg": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 180
                },
                "norad_id": {
                    "type": "string"
                }
            }
        },
        "gateway": {
            "type": "object",
            "required": ["id", "type"],
            "properties": {
                "id": {
                    "type": "string",
                    "minLength": 1
                },
                "type": {
                    "type": "string",
                    "enum": ["gateway", "ground_station", "terminal"]
                },
                "location": {
                    "type": "string"
                },
                "latitude": {
                    "type": "number",
                    "minimum": -90,
                    "maximum": 90
                },
                "longitude": {
                    "type": "number",
                    "minimum": -180,
                    "maximum": 180
                },
                "capacity_mbps": {
                    "type": "number",
                    "minimum": 0
                }
            }
        },
        "link": {
            "type": "object",
            "required": ["source", "target", "type"],
            "properties": {
                "source": {
                    "type": "string",
                    "minLength": 1
                },
                "target": {
                    "type": "string",
                    "minLength": 1
                },
                "type": {
                    "type": "string",
                    "enum": ["sat-ground", "sat-sat", "ground-ground"]
                },
                "bandwidth_mbps": {
                    "type": "number",
                    "minimum": 0
                },
                "latency_ms": {
                    "type": "number",
                    "minimum": 0
                }
            }
        },
        "event": {
            "type": "object",
            "required": ["time", "type", "source", "target"],
            "properties": {
                "time": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}([+-]\\d{2}:\\d{2}|Z)$"
                },
                "type": {
                    "type": "string",
                    "enum": ["link_up", "link_down", "handover", "failure", "recovery"]
                },
                "source": {
                    "type": "string",
                    "minLength": 1
                },
                "target": {
                    "type": "string",
                    "minLength": 1
                },
                "window_type": {
                    "type": "string",
                    "enum": ["cmd", "xband", "tle"]
                }
            }
        }
    }
}


# ============================================================================
# Metrics Output Schema
# ============================================================================

METRICS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Network Performance Metrics",
    "description": "KPIs from satellite network simulation",
    "type": "object",
    "required": ["total_sessions", "mode", "latency", "throughput"],
    "properties": {
        "total_sessions": {
            "type": "integer",
            "minimum": 0
        },
        "mode": {
            "type": "string",
            "enum": ["transparent", "regenerative"]
        },
        "latency": {
            "type": "object",
            "required": ["mean_ms", "min_ms", "max_ms", "p95_ms"],
            "properties": {
                "mean_ms": {
                    "type": "number",
                    "minimum": 0
                },
                "min_ms": {
                    "type": "number",
                    "minimum": 0
                },
                "max_ms": {
                    "type": "number",
                    "minimum": 0
                },
                "p95_ms": {
                    "type": "number",
                    "minimum": 0
                }
            }
        },
        "throughput": {
            "type": "object",
            "required": ["mean_mbps", "min_mbps", "max_mbps"],
            "properties": {
                "mean_mbps": {
                    "type": "number",
                    "minimum": 0
                },
                "min_mbps": {
                    "type": "number",
                    "minimum": 0
                },
                "max_mbps": {
                    "type": "number",
                    "minimum": 0
                }
            }
        },
        "total_duration_sec": {
            "type": "number",
            "minimum": 0
        }
    }
}


# ============================================================================
# Validation Functions
# ============================================================================

class ValidationError(Exception):
    """Custom exception for schema validation errors."""
    pass


def validate_windows(data: Dict[str, Any]) -> None:
    """Validate OASIS windows data against schema.

    Args:
        data: Parsed windows data with 'meta' and 'windows' keys

    Raises:
        ValidationError: If data does not conform to schema
    """
    try:
        jsonschema.validate(instance=data, schema=OASIS_WINDOW_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(
            f"Window validation failed: {e.message}\n"
            f"Path: {'.'.join(str(p) for p in e.path)}\n"
            f"Schema path: {'.'.join(str(p) for p in e.schema_path)}"
        ) from e
    except jsonschema.SchemaError as e:
        raise ValidationError(f"Invalid schema definition: {e.message}") from e


def validate_scenario(data: Dict[str, Any]) -> None:
    """Validate NS-3/SNS3 scenario configuration against schema.

    Args:
        data: Scenario configuration with metadata, topology, events, parameters

    Raises:
        ValidationError: If data does not conform to schema
    """
    try:
        jsonschema.validate(instance=data, schema=SCENARIO_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(
            f"Scenario validation failed: {e.message}\n"
            f"Path: {'.'.join(str(p) for p in e.path)}\n"
            f"Schema path: {'.'.join(str(p) for p in e.schema_path)}"
        ) from e
    except jsonschema.SchemaError as e:
        raise ValidationError(f"Invalid schema definition: {e.message}") from e


def validate_metrics(data: Dict[str, Any]) -> None:
    """Validate metrics output format against schema.

    Args:
        data: Metrics summary with latency, throughput, sessions

    Raises:
        ValidationError: If data does not conform to schema
    """
    try:
        jsonschema.validate(instance=data, schema=METRICS_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(
            f"Metrics validation failed: {e.message}\n"
            f"Path: {'.'.join(str(p) for p in e.path)}\n"
            f"Schema path: {'.'.join(str(p) for p in e.schema_path)}"
        ) from e
    except jsonschema.SchemaError as e:
        raise ValidationError(f"Invalid schema definition: {e.message}") from e


def validate_window_item(window: Dict[str, Any]) -> None:
    """Validate a single window object.

    Args:
        window: Single window dictionary

    Raises:
        ValidationError: If window does not conform to schema
    """
    try:
        jsonschema.validate(
            instance=window,
            schema=OASIS_WINDOW_SCHEMA["definitions"]["window"]
        )
    except jsonschema.ValidationError as e:
        raise ValidationError(
            f"Window item validation failed: {e.message}\n"
            f"Path: {'.'.join(str(p) for p in e.path)}"
        ) from e


# ============================================================================
# Utility Functions
# ============================================================================

def get_schema_version(schema: Dict[str, Any]) -> str:
    """Get JSON schema version from schema definition."""
    return schema.get("$schema", "unknown")


def list_required_fields(schema: Dict[str, Any]) -> List[str]:
    """Extract required fields from schema."""
    return schema.get("required", [])


def get_enum_values(schema: Dict[str, Any], field_path: str) -> List[Any]:
    """Get enum values for a specific field path.

    Args:
        schema: JSON schema
        field_path: Dot-separated path to field (e.g., 'metadata.mode')

    Returns:
        List of allowed enum values, or empty list if not an enum field
    """
    parts = field_path.split('.')
    current = schema.get('properties', {})

    for part in parts:
        if part in current:
            current = current[part]
            if 'properties' in current:
                current = current['properties']
        else:
            return []

    return current.get('enum', [])


if __name__ == "__main__":  # pragma: no cover
    # Quick schema validation test
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
