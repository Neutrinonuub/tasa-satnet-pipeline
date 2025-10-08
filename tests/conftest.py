"""Pytest configuration and shared fixtures."""
from __future__ import annotations
import pytest
from pathlib import Path
from datetime import datetime, timezone

# Test data directory
TEST_DIR = Path(__file__).parent
FIXTURES_DIR = TEST_DIR / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def sample_valid_log(fixtures_dir: Path) -> Path:
    """Path to valid OASIS log file."""
    return fixtures_dir / "valid_log.txt"


@pytest.fixture
def sample_malformed_log(fixtures_dir: Path) -> Path:
    """Path to malformed OASIS log file."""
    return fixtures_dir / "malformed_log.txt"


@pytest.fixture
def sample_edge_cases_log(fixtures_dir: Path) -> Path:
    """Path to edge cases OASIS log file."""
    return fixtures_dir / "edge_cases.txt"


@pytest.fixture
def valid_log_content() -> str:
    """Return valid OASIS log content."""
    return """
2025-01-08T10:00:00Z INFO: Mission OASIS-1 initialization
enter command window @ 2025-01-08T10:15:30Z sat=SAT-1 gw=HSINCHU
2025-01-08T10:16:00Z DEBUG: Uplink established
exit command window @ 2025-01-08T10:25:45Z sat=SAT-1 gw=HSINCHU
2025-01-08T10:30:00Z INFO: Data link window scheduled
X-band data link window: 2025-01-08T11:00:00Z..2025-01-08T11:08:30Z sat=SAT-1 gw=TAIPEI
enter command window @ 2025-01-08T12:00:00Z sat=SAT-2 gw=TAICHUNG
exit command window @ 2025-01-08T12:10:00Z sat=SAT-2 gw=TAICHUNG
X-band data link window: 2025-01-08T13:00:00Z..2025-01-08T13:15:00Z sat=SAT-2 gw=HSINCHU
"""


@pytest.fixture
def malformed_log_content() -> str:
    """Return malformed OASIS log content with various errors."""
    return """
enter command window @ INVALID-TIMESTAMP sat=SAT-1 gw=HSINCHU
exit command window @ 2025-01-08T10:25:45Z sat=SAT-1
X-band data link window: 2025-01-08T11:00:00Z..INVALID sat=SAT-1 gw=TAIPEI
enter command window @ 2025-01-08T12:00:00Z gw=TAICHUNG
"""


@pytest.fixture
def edge_cases_log_content() -> str:
    """Return edge cases log content."""
    return """
# Duplicate enters
enter command window @ 2025-01-08T10:00:00Z sat=SAT-1 gw=HSINCHU
enter command window @ 2025-01-08T10:01:00Z sat=SAT-1 gw=HSINCHU
exit command window @ 2025-01-08T10:05:00Z sat=SAT-1 gw=HSINCHU

# Missing exit
enter command window @ 2025-01-08T11:00:00Z sat=SAT-2 gw=TAIPEI

# Exit without enter
exit command window @ 2025-01-08T12:00:00Z sat=SAT-3 gw=TAICHUNG

# Overlapping windows
X-band data link window: 2025-01-08T13:00:00Z..2025-01-08T13:15:00Z sat=SAT-1 gw=HSINCHU
X-band data link window: 2025-01-08T13:10:00Z..2025-01-08T13:20:00Z sat=SAT-1 gw=HSINCHU

# Zero duration window
X-band data link window: 2025-01-08T14:00:00Z..2025-01-08T14:00:00Z sat=SAT-1 gw=TAIPEI
"""


@pytest.fixture
def expected_valid_windows() -> list[dict]:
    """Expected parsed windows from valid log."""
    return [
        {
            "type": "cmd",
            "start": "2025-01-08T10:15:30Z",
            "end": "2025-01-08T10:25:45Z",
            "sat": "SAT-1",
            "gw": "HSINCHU",
            "source": "log"
        },
        {
            "type": "xband",
            "start": "2025-01-08T11:00:00Z",
            "end": "2025-01-08T11:08:30Z",
            "sat": "SAT-1",
            "gw": "TAIPEI",
            "source": "log"
        },
        {
            "type": "cmd",
            "start": "2025-01-08T12:00:00Z",
            "end": "2025-01-08T12:10:00Z",
            "sat": "SAT-2",
            "gw": "TAICHUNG",
            "source": "log"
        },
        {
            "type": "xband",
            "start": "2025-01-08T13:00:00Z",
            "end": "2025-01-08T13:15:00Z",
            "sat": "SAT-2",
            "gw": "HSINCHU",
            "source": "log"
        }
    ]


@pytest.fixture
def temp_log_file(tmp_path: Path, valid_log_content: str) -> Path:
    """Create a temporary log file with valid content."""
    log_file = tmp_path / "test.log"
    log_file.write_text(valid_log_content, encoding="utf-8")
    return log_file


@pytest.fixture
def temp_output_file(tmp_path: Path) -> Path:
    """Create a temporary output file path."""
    return tmp_path / "output.json"
