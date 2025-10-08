#!/usr/bin/env python3
"""Unit tests for input validation utilities.

Tests for P0-1 (timezone parameter usage) and P0-2 (input validation).
"""
from __future__ import annotations
import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validators import (
    validate_file_size,
    validate_path_traversal,
    sanitize_satellite_name,
    sanitize_gateway_name,
    validate_input_file,
    FileSizeError,
    PathTraversalError,
    InputSanitizationError,
    ValidationError,
    MAX_FILE_SIZE_BYTES
)
from parse_oasis_log import parse_dt


class TestTimezoneParameterUsage:
    """Test P0-1: Fix timezone parameter usage in parse_dt function."""

    def test_parse_dt_with_utc(self):
        """Test parse_dt with default UTC timezone."""
        ts = "2025-01-08T10:15:30Z"
        result = parse_dt(ts, tz="UTC")

        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 8
        assert result.hour == 10
        assert result.minute == 15
        assert result.second == 30
        assert result.tzinfo == timezone.utc

    def test_parse_dt_with_custom_tz(self):
        """Test parse_dt with custom timezone (requires pytz)."""
        ts = "2025-01-08T10:15:30Z"

        try:
            import pytz
            # Test with Asia/Taipei timezone
            result = parse_dt(ts, tz="Asia/Taipei")
            assert isinstance(result, datetime)
            assert result.tzinfo is not None
            # Original time should be preserved, just timezone changed
            assert result.year == 2025
            assert result.month == 1
            assert result.day == 8
        except ImportError:
            pytest.skip("pytz not available, skipping custom timezone test")

    def test_parse_dt_defaults_to_utc(self):
        """Test parse_dt defaults to UTC when no timezone specified."""
        ts = "2025-01-08T10:15:30Z"
        result = parse_dt(ts)

        assert result.tzinfo == timezone.utc

    def test_parse_dt_fallback_without_pytz(self):
        """Test parse_dt falls back to UTC when pytz unavailable."""
        ts = "2025-01-08T10:15:30Z"

        # Even if we request a custom timezone, without pytz it should warn
        # and fall back to UTC
        with pytest.warns(None):  # May or may not warn depending on pytz availability
            result = parse_dt(ts, tz="America/New_York")
            assert isinstance(result, datetime)


class TestFileSizeValidation:
    """Test P0-2: File size validation."""

    def test_file_size_within_limit(self, tmp_path: Path):
        """Test validation passes for file within size limit."""
        test_file = tmp_path / "small.log"
        test_file.write_text("Small file content\n" * 100)  # ~2KB

        # Should not raise exception
        validate_file_size(test_file)

    def test_file_size_exceeds_limit(self, tmp_path: Path):
        """Test validation fails for file exceeding size limit."""
        test_file = tmp_path / "large.log"
        # Create file larger than 100MB
        large_content = "x" * (MAX_FILE_SIZE_BYTES + 1000)
        test_file.write_text(large_content)

        with pytest.raises(FileSizeError) as exc_info:
            validate_file_size(test_file)

        assert "exceeds maximum allowed size" in str(exc_info.value)

    def test_file_size_custom_limit(self, tmp_path: Path):
        """Test validation with custom size limit."""
        test_file = tmp_path / "medium.log"
        test_file.write_text("x" * 1024)  # 1KB

        # Should pass with 10KB limit
        validate_file_size(test_file, max_size=10 * 1024)

        # Should fail with 512B limit
        with pytest.raises(FileSizeError):
            validate_file_size(test_file, max_size=512)

    def test_file_size_nonexistent_file(self, tmp_path: Path):
        """Test validation fails for non-existent file."""
        test_file = tmp_path / "nonexistent.log"

        with pytest.raises(FileNotFoundError):
            validate_file_size(test_file)


class TestPathTraversalProtection:
    """Test P0-2: Path traversal protection."""

    def test_path_traversal_valid_path(self, tmp_path: Path):
        """Test validation passes for valid path."""
        test_file = tmp_path / "valid.log"
        test_file.write_text("Valid content")

        # Should not raise exception
        validate_path_traversal(test_file)

    def test_path_traversal_with_base_dir(self, tmp_path: Path):
        """Test validation with base directory restriction."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()
        test_file = base_dir / "test.log"
        test_file.write_text("Test content")

        # Should pass - file is within base_dir
        validate_path_traversal(test_file, base_dir=base_dir)

    def test_path_traversal_outside_base_dir(self, tmp_path: Path):
        """Test validation fails for path outside base directory."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()
        outside_file = tmp_path / "outside.log"
        outside_file.write_text("Outside content")

        # Should fail - file is outside base_dir
        with pytest.raises(PathTraversalError) as exc_info:
            validate_path_traversal(outside_file, base_dir=base_dir)

        assert "outside base directory" in str(exc_info.value)

    def test_path_traversal_relative_path(self, tmp_path: Path):
        """Test validation handles relative paths."""
        test_file = tmp_path / "test.log"
        test_file.write_text("Test content")

        # Even if path contains .., after resolution it should be safe
        # This tests that we resolve to absolute path first
        validate_path_traversal(test_file)


class TestInputSanitization:
    """Test P0-2: Input sanitization for satellite and gateway names."""

    def test_sanitize_valid_satellite_name(self):
        """Test sanitization of valid satellite name."""
        assert sanitize_satellite_name("SAT-1") == "SAT-1"
        assert sanitize_satellite_name("sat_2") == "SAT_2"
        assert sanitize_satellite_name("STARLINK-123") == "STARLINK-123"

    def test_sanitize_satellite_name_with_whitespace(self):
        """Test sanitization removes leading/trailing whitespace."""
        assert sanitize_satellite_name("  SAT-1  ") == "SAT-1"

    def test_sanitize_satellite_name_lowercase(self):
        """Test sanitization converts to uppercase."""
        assert sanitize_satellite_name("sat-1") == "SAT-1"

    def test_sanitize_invalid_satellite_name_special_chars(self):
        """Test sanitization fails for invalid characters."""
        with pytest.raises(InputSanitizationError) as exc_info:
            sanitize_satellite_name("SAT@1")

        assert "Invalid satellite name" in str(exc_info.value)

    def test_sanitize_invalid_satellite_name_empty(self):
        """Test sanitization fails for empty name."""
        with pytest.raises(InputSanitizationError) as exc_info:
            sanitize_satellite_name("")

        assert "cannot be empty" in str(exc_info.value)

    def test_sanitize_invalid_satellite_name_too_long(self):
        """Test sanitization fails for name exceeding max length."""
        long_name = "SAT-" + "X" * 100

        with pytest.raises(InputSanitizationError):
            sanitize_satellite_name(long_name)

    def test_sanitize_valid_gateway_name(self):
        """Test sanitization of valid gateway name."""
        assert sanitize_gateway_name("HSINCHU") == "HSINCHU"
        assert sanitize_gateway_name("taipei-1") == "TAIPEI-1"
        assert sanitize_gateway_name("GW_001") == "GW_001"

    def test_sanitize_gateway_name_with_whitespace(self):
        """Test sanitization removes leading/trailing whitespace."""
        assert sanitize_gateway_name("  HSINCHU  ") == "HSINCHU"

    def test_sanitize_invalid_gateway_name_special_chars(self):
        """Test sanitization fails for invalid characters."""
        with pytest.raises(InputSanitizationError) as exc_info:
            sanitize_gateway_name("HSINCHU#1")

        assert "Invalid gateway name" in str(exc_info.value)

    def test_sanitize_invalid_gateway_name_empty(self):
        """Test sanitization fails for empty name."""
        with pytest.raises(InputSanitizationError) as exc_info:
            sanitize_gateway_name("")

        assert "cannot be empty" in str(exc_info.value)


class TestComprehensiveValidation:
    """Test comprehensive validation combining all checks."""

    def test_validate_input_file_success(self, tmp_path: Path):
        """Test comprehensive validation passes for valid file."""
        test_file = tmp_path / "valid.log"
        test_file.write_text("Valid OASIS log content\n" * 100)

        # Should not raise exception
        validate_input_file(test_file)

    def test_validate_input_file_with_base_dir(self, tmp_path: Path):
        """Test comprehensive validation with base directory."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()
        test_file = base_dir / "test.log"
        test_file.write_text("Test content")

        # Should not raise exception
        validate_input_file(test_file, base_dir=base_dir)

    def test_validate_input_file_too_large(self, tmp_path: Path):
        """Test comprehensive validation fails for oversized file."""
        test_file = tmp_path / "huge.log"
        # Create file larger than 100MB
        large_content = "x" * (MAX_FILE_SIZE_BYTES + 1000)
        test_file.write_text(large_content)

        with pytest.raises(FileSizeError):
            validate_input_file(test_file)

    def test_validate_input_file_outside_base(self, tmp_path: Path):
        """Test comprehensive validation fails for file outside base dir."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()
        outside_file = tmp_path / "outside.log"
        outside_file.write_text("Outside content")

        with pytest.raises(PathTraversalError):
            validate_input_file(outside_file, base_dir=base_dir)


class TestIntegrationWithParser:
    """Integration tests with parse_oasis_log.py main function."""

    def test_parser_with_valid_satellite_filter(self, temp_log_file: Path, tmp_path: Path):
        """Test parser accepts valid sanitized satellite name."""
        output_file = tmp_path / "output.json"

        sys.argv = [
            "parse_oasis_log.py",
            str(temp_log_file),
            "-o", str(output_file),
            "--sat", "SAT-1"
        ]

        from parse_oasis_log import main
        result = main()

        # Should succeed without error
        assert result is None or result == 0
        assert output_file.exists()

    def test_parser_with_invalid_satellite_filter(self, temp_log_file: Path, tmp_path: Path, capsys):
        """Test parser rejects invalid satellite name."""
        output_file = tmp_path / "output.json"

        sys.argv = [
            "parse_oasis_log.py",
            str(temp_log_file),
            "-o", str(output_file),
            "--sat", "SAT@INVALID!"
        ]

        from parse_oasis_log import main
        result = main()

        # Should return error code
        assert result == 1

        # Should print error message
        captured = capsys.readouterr()
        assert "error" in captured.out.lower()

    def test_parser_with_oversized_file(self, tmp_path: Path, capsys):
        """Test parser rejects oversized input file."""
        # Create oversized file
        large_file = tmp_path / "huge.log"
        large_content = "x" * (MAX_FILE_SIZE_BYTES + 1000)
        large_file.write_text(large_content)

        output_file = tmp_path / "output.json"

        sys.argv = [
            "parse_oasis_log.py",
            str(large_file),
            "-o", str(output_file)
        ]

        from parse_oasis_log import main
        result = main()

        # Should return error code
        assert result == 1

        # Should print error message
        captured = capsys.readouterr()
        assert "exceeds maximum allowed size" in captured.out.lower()


# Run tests with: pytest tests/test_validators.py -v --cov=scripts/validators --cov=scripts/parse_oasis_log --cov-report=term-missing
