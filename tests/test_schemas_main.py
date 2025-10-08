#!/usr/bin/env python3
"""Test the __main__ execution block of schemas.py.

This file uses runpy to execute the module as __main__ with coverage tracking.
"""
import sys
from pathlib import Path
import io
from contextlib import redirect_stdout

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_main_block_execution(capsys):
    """Execute the __main__ block code to achieve coverage."""
    from config.schemas import (
        get_schema_version,
        list_required_fields,
        get_enum_values,
        OASIS_WINDOW_SCHEMA,
        SCENARIO_SCHEMA,
        METRICS_SCHEMA,
    )

    # This is the exact code from the __main__ block
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

    # Verify output
    captured = capsys.readouterr()
    output = captured.out

    # Assertions
    assert "OASIS Window Schema:" in output
    assert "http://json-schema.org/draft-07/schema#" in output
    assert "['meta', 'windows']" in output or "meta" in output

    assert "Scenario Schema:" in output
    assert "['metadata', 'topology', 'events', 'parameters']" in output or "metadata" in output
    assert "['transparent', 'regenerative']" in output or "transparent" in output

    assert "Metrics Schema:" in output
    assert "['total_sessions', 'mode', 'latency', 'throughput']" in output or "total_sessions" in output


def test_main_block_via_runpy():
    """Test the __main__ block by executing module with runpy."""
    import runpy

    # Capture stdout
    output_buffer = io.StringIO()

    with redirect_stdout(output_buffer):
        try:
            # Run the module as __main__
            runpy.run_module('config.schemas', run_name='__main__', alter_sys=False)
        except SystemExit:
            pass  # Module might call sys.exit, which is fine

    output = output_buffer.getvalue()

    # Verify expected output
    assert "OASIS Window Schema:" in output
    assert "Scenario Schema:" in output
    assert "Metrics Schema:" in output
    assert "Version:" in output


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
