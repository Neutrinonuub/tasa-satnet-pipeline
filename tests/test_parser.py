"""Unit tests for OASIS log parser - TDD approach."""
from __future__ import annotations
import pytest
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from parse_oasis_log import (
    parse_dt,
    PAT_ENTER,
    PAT_EXIT,
    PAT_XBAND,
    main
)


class TestTimestampParsing:
    """Test timestamp parsing functionality."""
    
    def test_parse_valid_timestamp(self):
        """Test parsing valid ISO 8601 timestamp."""
        ts = "2025-01-08T10:15:30Z"
        result = parse_dt(ts)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 8
        assert result.hour == 10
        assert result.minute == 15
        assert result.second == 30
        assert result.tzinfo == timezone.utc
    
    def test_parse_invalid_timestamp(self):
        """Test parsing invalid timestamp raises ValueError."""
        with pytest.raises(ValueError):
            parse_dt("INVALID-TIMESTAMP")
    
    def test_parse_wrong_format(self):
        """Test parsing timestamp with wrong format."""
        with pytest.raises(ValueError):
            parse_dt("2025/01/08 10:15:30")


class TestRegexPatterns:
    """Test regex pattern matching."""
    
    def test_enter_command_window_pattern(self):
        """Test enter command window pattern matching."""
        line = "enter command window @ 2025-01-08T10:15:30Z sat=SAT-1 gw=HSINCHU"
        match = PAT_ENTER.search(line)
        assert match is not None
        assert match.group(1) == "2025-01-08T10:15:30Z"
        assert match.group(2) == "SAT-1"
        assert match.group(3) == "HSINCHU"
    
    def test_exit_command_window_pattern(self):
        """Test exit command window pattern matching."""
        line = "exit command window @ 2025-01-08T10:25:45Z sat=SAT-1 gw=HSINCHU"
        match = PAT_EXIT.search(line)
        assert match is not None
        assert match.group(1) == "2025-01-08T10:25:45Z"
        assert match.group(2) == "SAT-1"
        assert match.group(3) == "HSINCHU"
    
    def test_xband_window_pattern(self):
        """Test X-band data link window pattern matching."""
        line = "X-band data link window: 2025-01-08T11:00:00Z..2025-01-08T11:08:30Z sat=SAT-1 gw=TAIPEI"
        match = PAT_XBAND.search(line)
        assert match is not None
        assert match.group(1) == "2025-01-08T11:00:00Z"
        assert match.group(2) == "2025-01-08T11:08:30Z"
        assert match.group(3) == "SAT-1"
        assert match.group(4) == "TAIPEI"
    
    def test_pattern_case_insensitive(self):
        """Test patterns are case-insensitive."""
        line = "ENTER COMMAND WINDOW @ 2025-01-08T10:15:30Z SAT=SAT-1 GW=HSINCHU"
        match = PAT_ENTER.search(line)
        assert match is not None
    
    def test_pattern_with_extra_whitespace(self):
        """Test patterns handle extra whitespace."""
        line = "enter  command  window  @  2025-01-08T10:15:30Z  sat=SAT-1  gw=HSINCHU"
        match = PAT_ENTER.search(line)
        assert match is not None
    
    def test_pattern_no_match_invalid_line(self):
        """Test patterns don't match invalid lines."""
        line = "This is not a valid window line"
        assert PAT_ENTER.search(line) is None
        assert PAT_EXIT.search(line) is None
        assert PAT_XBAND.search(line) is None


class TestParserLogic:
    """Test main parser logic."""
    
    def test_parse_valid_log(self, temp_log_file: Path, temp_output_file: Path):
        """Test parsing valid log file."""
        sys.argv = [
            "parse_oasis_log.py",
            str(temp_log_file),
            "-o", str(temp_output_file)
        ]
        
        # Should not raise exception
        main()
        
        # Check output file exists
        assert temp_output_file.exists()
        
        # Validate JSON structure
        with open(temp_output_file) as f:
            data = json.load(f)
        
        assert "meta" in data
        assert "windows" in data
        assert data["meta"]["count"] == len(data["windows"])
        assert isinstance(data["windows"], list)
    
    def test_parse_output_structure(self, temp_log_file: Path, temp_output_file: Path):
        """Test output JSON has correct structure."""
        sys.argv = [
            "parse_oasis_log.py",
            str(temp_log_file),
            "-o", str(temp_output_file)
        ]
        main()
        
        with open(temp_output_file) as f:
            data = json.load(f)
        
        # Check meta structure
        assert "source" in data["meta"]
        assert "count" in data["meta"]
        
        # Check windows structure
        for window in data["windows"]:
            assert "type" in window
            assert window["type"] in ["cmd", "xband"]
            assert "sat" in window
            assert "gw" in window
            assert "source" in window
            
            if window["type"] == "cmd" or window["type"] == "xband":
                assert "start" in window
                assert "end" in window
    
    def test_parse_window_count(self, temp_log_file: Path, temp_output_file: Path):
        """Test correct number of windows parsed."""
        sys.argv = [
            "parse_oasis_log.py",
            str(temp_log_file),
            "-o", str(temp_output_file)
        ]
        main()
        
        with open(temp_output_file) as f:
            data = json.load(f)
        
        # Expected: 2 cmd windows + 2 xband windows = 4 total
        assert data["meta"]["count"] == 4
        assert len(data["windows"]) == 4
    
    def test_parse_filters_by_satellite(self, temp_log_file: Path, temp_output_file: Path):
        """Test filtering by satellite ID."""
        sys.argv = [
            "parse_oasis_log.py",
            str(temp_log_file),
            "-o", str(temp_output_file),
            "--sat", "SAT-1"
        ]
        main()
        
        with open(temp_output_file) as f:
            data = json.load(f)
        
        # All windows should be for SAT-1
        for window in data["windows"]:
            assert window["sat"] == "SAT-1"
    
    def test_parse_filters_by_gateway(self, temp_log_file: Path, temp_output_file: Path):
        """Test filtering by gateway ID."""
        sys.argv = [
            "parse_oasis_log.py",
            str(temp_log_file),
            "-o", str(temp_output_file),
            "--gw", "HSINCHU"
        ]
        main()
        
        with open(temp_output_file) as f:
            data = json.load(f)
        
        # All windows should be for HSINCHU gateway
        for window in data["windows"]:
            assert window["gw"] == "HSINCHU"
    
    def test_parse_filters_by_min_duration(self, temp_log_file: Path, temp_output_file: Path):
        """Test filtering by minimum duration."""
        sys.argv = [
            "parse_oasis_log.py",
            str(temp_log_file),
            "-o", str(temp_output_file),
            "--min-duration", "600"  # 10 minutes
        ]
        main()
        
        with open(temp_output_file) as f:
            data = json.load(f)
        
        # All windows should have duration >= 600 seconds
        for window in data["windows"]:
            if window.get("start") and window.get("end"):
                start = parse_dt(window["start"])
                end = parse_dt(window["end"])
                duration = (end - start).total_seconds()
                assert duration >= 600
    
    def test_parse_empty_log(self, tmp_path: Path):
        """Test parsing empty log file."""
        empty_log = tmp_path / "empty.log"
        empty_log.write_text("", encoding="utf-8")
        output_file = tmp_path / "output.json"
        
        sys.argv = [
            "parse_oasis_log.py",
            str(empty_log),
            "-o", str(output_file)
        ]
        main()
        
        with open(output_file) as f:
            data = json.load(f)
        
        assert data["meta"]["count"] == 0
        assert len(data["windows"]) == 0
    
    def test_parse_nonexistent_file(self, tmp_path: Path):
        """Test parsing non-existent file raises error."""
        nonexistent = tmp_path / "nonexistent.log"
        output_file = tmp_path / "output.json"
        
        sys.argv = [
            "parse_oasis_log.py",
            str(nonexistent),
            "-o", str(output_file)
        ]
        
        with pytest.raises(FileNotFoundError):
            main()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_parse_duplicate_enters(self, tmp_path: Path, edge_cases_log_content: str):
        """Test handling duplicate enter commands."""
        log_file = tmp_path / "edge.log"
        log_file.write_text(edge_cases_log_content, encoding="utf-8")
        output_file = tmp_path / "output.json"
        
        sys.argv = [
            "parse_oasis_log.py",
            str(log_file),
            "-o", str(output_file)
        ]
        
        # Should not raise exception
        main()
        
        # Verify output
        with open(output_file) as f:
            data = json.load(f)
        
        # Should handle gracefully (implementation-dependent)
        assert isinstance(data["windows"], list)
    
    def test_parse_missing_exit(self, tmp_path: Path):
        """Test handling enter without matching exit."""
        log_content = "enter command window @ 2025-01-08T10:00:00Z sat=SAT-1 gw=HSINCHU\n"
        log_file = tmp_path / "missing_exit.log"
        log_file.write_text(log_content, encoding="utf-8")
        output_file = tmp_path / "output.json"
        
        sys.argv = [
            "parse_oasis_log.py",
            str(log_file),
            "-o", str(output_file)
        ]
        main()
        
        # Should complete without error
        assert output_file.exists()
    
    def test_parse_exit_without_enter(self, tmp_path: Path):
        """Test handling exit without matching enter."""
        log_content = "exit command window @ 2025-01-08T10:00:00Z sat=SAT-1 gw=HSINCHU\n"
        log_file = tmp_path / "orphan_exit.log"
        log_file.write_text(log_content, encoding="utf-8")
        output_file = tmp_path / "output.json"
        
        sys.argv = [
            "parse_oasis_log.py",
            str(log_file),
            "-o", str(output_file)
        ]
        main()
        
        # Should complete without error
        assert output_file.exists()
    
    def test_parse_overlapping_windows(self, tmp_path: Path):
        """Test handling overlapping time windows."""
        log_content = """
X-band data link window: 2025-01-08T10:00:00Z..2025-01-08T10:15:00Z sat=SAT-1 gw=HSINCHU
X-band data link window: 2025-01-08T10:10:00Z..2025-01-08T10:20:00Z sat=SAT-1 gw=HSINCHU
"""
        log_file = tmp_path / "overlap.log"
        log_file.write_text(log_content, encoding="utf-8")
        output_file = tmp_path / "output.json"
        
        sys.argv = [
            "parse_oasis_log.py",
            str(log_file),
            "-o", str(output_file)
        ]
        main()
        
        with open(output_file) as f:
            data = json.load(f)
        
        # Should preserve both windows
        assert len(data["windows"]) == 2
    
    def test_parse_zero_duration_window(self, tmp_path: Path):
        """Test handling zero-duration windows."""
        log_content = "X-band data link window: 2025-01-08T10:00:00Z..2025-01-08T10:00:00Z sat=SAT-1 gw=HSINCHU\n"
        log_file = tmp_path / "zero_duration.log"
        log_file.write_text(log_content, encoding="utf-8")
        output_file = tmp_path / "output.json"
        
        sys.argv = [
            "parse_oasis_log.py",
            str(log_file),
            "-o", str(output_file),
            "--min-duration", "0"
        ]
        main()
        
        with open(output_file) as f:
            data = json.load(f)
        
        # Should include or filter based on min-duration
        assert isinstance(data["windows"], list)


class TestPerformance:
    """Performance and scalability tests."""
    
    def test_parse_large_log_performance(self, tmp_path: Path, benchmark):
        """Test parsing performance with large log file."""
        # Generate large log file (1000 windows)
        log_content = []
        for i in range(500):
            ts_start = f"2025-01-08T{10 + i % 14:02d}:{i % 60:02d}:00Z"
            ts_end = f"2025-01-08T{10 + i % 14:02d}:{(i + 10) % 60:02d}:00Z"
            log_content.append(f"enter command window @ {ts_start} sat=SAT-{i%10} gw=GW-{i%5}")
            log_content.append(f"exit command window @ {ts_end} sat=SAT-{i%10} gw=GW-{i%5}")
        
        log_file = tmp_path / "large.log"
        log_file.write_text("\n".join(log_content), encoding="utf-8")
        output_file = tmp_path / "output.json"
        
        def parse():
            sys.argv = [
                "parse_oasis_log.py",
                str(log_file),
                "-o", str(output_file)
            ]
            main()
        
        # Benchmark should complete in reasonable time
        result = benchmark(parse)
        
        # Verify output
        with open(output_file) as f:
            data = json.load(f)
        assert data["meta"]["count"] > 0
    
    def test_parse_memory_efficiency(self, tmp_path: Path):
        """Test memory efficiency with large files."""
        # This test would require memory profiling
        # Placeholder for now
        pass


# Run tests with: pytest tests/test_parser.py -v --cov=scripts
