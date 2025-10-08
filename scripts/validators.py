#!/usr/bin/env python3
"""Input validation utilities for OASIS log parser.

Provides validation for:
- File size limits
- Path traversal protection
- Input sanitization for satellite names and gateway IDs
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional


# Security constants
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
ALLOWED_SATELLITE_PATTERN = re.compile(r'^[A-Z0-9_-]{1,50}$', re.IGNORECASE)
ALLOWED_GATEWAY_PATTERN = re.compile(r'^[A-Z0-9_-]{1,50}$', re.IGNORECASE)


class ValidationError(Exception):
    """Base exception for validation errors."""
    pass


class FileSizeError(ValidationError):
    """Raised when file exceeds maximum size limit."""
    pass


class PathTraversalError(ValidationError):
    """Raised when path contains traversal attempts."""
    pass


class InputSanitizationError(ValidationError):
    """Raised when input contains invalid characters."""
    pass


def validate_file_size(file_path: Path, max_size: int = MAX_FILE_SIZE_BYTES) -> None:
    """Validate that file size does not exceed maximum limit.

    Args:
        file_path: Path to file to validate
        max_size: Maximum allowed file size in bytes (default: 100MB)

    Raises:
        FileSizeError: If file size exceeds max_size
        FileNotFoundError: If file does not exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = file_path.stat().st_size
    if file_size > max_size:
        raise FileSizeError(
            f"File size ({file_size} bytes) exceeds maximum allowed size "
            f"({max_size} bytes / {max_size / (1024*1024):.1f} MB)"
        )


def validate_path_traversal(file_path: Path, base_dir: Optional[Path] = None) -> None:
    """Validate that file path does not contain path traversal attempts.

    Args:
        file_path: Path to validate
        base_dir: Optional base directory to ensure path is within

    Raises:
        PathTraversalError: If path contains traversal attempts or is outside base_dir
    """
    # Resolve to absolute path
    resolved_path = file_path.resolve()

    # Check for path traversal patterns
    path_str = str(resolved_path)
    if '..' in path_str or '//' in path_str or '\\\\' in path_str:
        raise PathTraversalError(
            f"Path contains traversal patterns: {file_path}"
        )

    # If base_dir specified, ensure path is within it
    if base_dir is not None:
        base_resolved = base_dir.resolve()
        try:
            resolved_path.relative_to(base_resolved)
        except ValueError:
            raise PathTraversalError(
                f"Path {file_path} is outside base directory {base_dir}"
            )


def sanitize_satellite_name(sat_name: str) -> str:
    """Sanitize and validate satellite name.

    Args:
        sat_name: Satellite name to sanitize

    Returns:
        Sanitized satellite name

    Raises:
        InputSanitizationError: If satellite name contains invalid characters
    """
    if not sat_name:
        raise InputSanitizationError("Satellite name cannot be empty")

    # Remove leading/trailing whitespace
    sat_name = sat_name.strip()

    # Validate against allowed pattern
    if not ALLOWED_SATELLITE_PATTERN.match(sat_name):
        raise InputSanitizationError(
            f"Invalid satellite name '{sat_name}'. "
            f"Must contain only alphanumeric characters, hyphens, and underscores "
            f"(max 50 characters)"
        )

    return sat_name.upper()


def sanitize_gateway_name(gw_name: str) -> str:
    """Sanitize and validate gateway name.

    Args:
        gw_name: Gateway name to sanitize

    Returns:
        Sanitized gateway name

    Raises:
        InputSanitizationError: If gateway name contains invalid characters
    """
    if not gw_name:
        raise InputSanitizationError("Gateway name cannot be empty")

    # Remove leading/trailing whitespace
    gw_name = gw_name.strip()

    # Validate against allowed pattern
    if not ALLOWED_GATEWAY_PATTERN.match(gw_name):
        raise InputSanitizationError(
            f"Invalid gateway name '{gw_name}'. "
            f"Must contain only alphanumeric characters, hyphens, and underscores "
            f"(max 50 characters)"
        )

    return gw_name.upper()


def validate_input_file(file_path: Path, base_dir: Optional[Path] = None) -> None:
    """Comprehensive validation for input file.

    Performs all validation checks:
    - File existence
    - File size limit
    - Path traversal protection

    Args:
        file_path: Path to input file
        base_dir: Optional base directory to restrict paths to

    Raises:
        ValidationError: If any validation check fails
    """
    validate_path_traversal(file_path, base_dir)
    validate_file_size(file_path)
