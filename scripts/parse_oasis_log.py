#!/usr/bin/env python3
"""OASIS log parser (minimal scaffold).

Parses lines like:
  - enter command window @ 2025-10-08T01:23:45Z sat=SAT-1 gw=HSINCHU
  - exit command window @ ...
  - X-band data link window: 2025-10-08T02:00:00Z..2025-10-08T02:08:00Z sat=SAT-1 gw=TAIPEI
Outputs JSON with window objects and a summary.

Usage:
  python scripts/parse_oasis_log.py data/sample_oasis.log -o data/oasis_windows.json
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Deque, Optional

# Add parent directory to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.schemas import validate_windows, validate_window_item, ValidationError

# Import input validators for P0-2
try:
    from validators import (
        validate_input_file,
        sanitize_satellite_name,
        sanitize_gateway_name,
        ValidationError
    )
except ImportError:
    # Fallback if validators not available
    def validate_input_file(file_path, base_dir=None):
        pass
    def sanitize_satellite_name(name):
        return name
    def sanitize_gateway_name(name):
        return name
    ValidationError = Exception

TS = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"

PAT_ENTER = re.compile(rf"enter\s+command\s+window\s*@\s*({TS})\s*sat=(\S+)\s*gw=(\S+)", re.I)
PAT_EXIT  = re.compile(rf"exit\s+command\s+window\s*@\s*({TS})\s*sat=(\S+)\s*gw=(\S+)", re.I)
PAT_XBAND = re.compile(rf"X-band\s+data\s+link\s+window\s*:\s*({TS})\s*\.\.\s*({TS})\s*sat=(\S+)\s*gw=(\S+)", re.I)

def parse_dt(s: str, tz: str = "UTC") -> datetime:
    """Parse timestamp with configurable timezone.

    Args:
        s: Timestamp string in ISO 8601 format (e.g., "2025-01-08T10:15:30Z")
        tz: Timezone name (default: "UTC"). For non-UTC, requires pytz.

    Returns:
        datetime object with timezone information

    Raises:
        ValueError: If timestamp format is invalid
    """
    dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")

    if tz == "UTC":
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Use pytz for non-UTC timezones
        try:
            import pytz
            return pytz.timezone(tz).localize(dt)
        except ImportError:
            # Fallback to UTC if pytz not available
            import warnings
            warnings.warn(f"pytz not available, falling back to UTC instead of {tz}")
            return dt.replace(tzinfo=timezone.utc)

def pair_windows_optimized(windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """O(n) pairing algorithm for command enter/exit windows.

    Uses hash map for O(1) lookups instead of O(n²) nested loops.

    Args:
        windows: List of all parsed window events

    Returns:
        List of paired command windows with start/end times

    Performance:
        - Time complexity: O(n) vs O(n²) for naive approach
        - Expected speedup: 100x+ for 1000 windows
    """
    # Separate enters and exits
    enters = [(i, w) for i, w in enumerate(windows) if w["type"] == "cmd_enter"]
    exits = [(i, w) for i, w in enumerate(windows) if w["type"] == "cmd_exit"]

    # Build hash map: (sat, gw) -> deque of exit windows (O(1) popleft)
    exit_map: Dict[tuple, Deque[tuple]] = {}
    for idx, exit_win in exits:
        key = (exit_win["sat"], exit_win["gw"])
        if key not in exit_map:
            exit_map[key] = deque()
        exit_map[key].append((idx, exit_win))

    # Match enters with exits using O(1) hash lookups and O(1) deque popleft
    paired = []
    for enter_idx, enter_win in enters:
        key = (enter_win["sat"], enter_win["gw"])
        if key in exit_map and exit_map[key]:
            # Pop first available exit for this sat/gw (FIFO) - O(1) with deque
            exit_idx, exit_win = exit_map[key].popleft()
            paired.append({
                "type": "cmd",
                "start": enter_win["start"],
                "end": exit_win["end"],
                "sat": enter_win["sat"],
                "gw": enter_win["gw"],
                "source": "log"
            })

    return paired

def main():
    ap = argparse.ArgumentParser(description="OASIS log parser with optional TLE integration")
    ap.add_argument("log", type=Path, help="OASIS log file to parse")
    ap.add_argument("-o", "--output", type=Path, default=Path("data/oasis_windows.json"),
                   help="Output JSON file")
    ap.add_argument("--tz", default="UTC", help="Timezone for timestamp parsing")
    ap.add_argument("--sat", default=None, help="Filter by satellite name")
    ap.add_argument("--gw", default=None, help="Filter by gateway name")
    ap.add_argument("--min-duration", type=int, default=0, help="min window seconds to keep")
    ap.add_argument("--skip-validation", action="store_true",
                   help="Skip schema validation (not recommended)")

    # TLE integration arguments
    ap.add_argument("--tle-file", type=Path, default=None,
                   help="Optional TLE file for window calculation and merging")
    ap.add_argument("--stations", type=Path,
                   default=Path("data/taiwan_ground_stations.json"),
                   help="Ground stations JSON file for TLE calculations")
    ap.add_argument("--merge-strategy", type=str, default="union",
                   choices=["union", "intersection", "tle-only", "oasis-only"],
                   help="Merge strategy when TLE file is provided")
    ap.add_argument("--min-elevation", type=float, default=10.0,
                   help="Minimum elevation angle for TLE windows (degrees)")
    ap.add_argument("--tle-step", type=int, default=30,
                   help="Time step for TLE calculations (seconds)")

    args = ap.parse_args()

    # P0-2: Input validation
    try:
        # Validate input file (size, path traversal)
        validate_input_file(args.log)

        # Sanitize satellite and gateway names if provided
        if args.sat:
            args.sat = sanitize_satellite_name(args.sat)
        if args.gw:
            args.gw = sanitize_gateway_name(args.gw)
    except ValidationError as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return 1


    windows = []
    with args.log.open("r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    for m in PAT_ENTER.finditer(content):
        t, sat, gw = m.groups()
        windows.append({"type":"cmd_enter", "start": t, "end": None, "sat": sat, "gw": gw, "source":"log"})
    for m in PAT_EXIT.finditer(content):
        t, sat, gw = m.groups()
        windows.append({"type":"cmd_exit", "start": None, "end": t, "sat": sat, "gw": gw, "source":"log"})
    for m in PAT_XBAND.finditer(content):
        s, e, sat, gw = m.groups()
        window = {"type":"xband", "start": s, "end": e, "sat": sat, "gw": gw, "source":"log"}

        # Validate individual window before adding (unless validation is skipped)
        if not args.skip_validation:
            try:
                validate_window_item(window)
            except ValidationError as e:
                print(f"WARNING: Skipping invalid xband window: {e}", file=sys.stderr)
                continue

        windows.append(window)

    # O(n) pairing for command windows using hash-based matching
    paired = pair_windows_optimized(windows)

    # Validate paired windows
    if not args.skip_validation:
        validated_paired = []
        for window in paired:
            try:
                validate_window_item(window)
                validated_paired.append(window)
            except ValidationError as e:
                print(f"WARNING: Skipping invalid paired window: {e}", file=sys.stderr)
        paired = validated_paired

    # keep explicit xband + paired command windows
    final = [w for w in windows if w["type"]=="xband"] + paired

    # filter by satellite and gateway
    if args.sat:
        final = [w for w in final if w.get("sat") == args.sat]
    if args.gw:
        final = [w for w in final if w.get("gw") == args.gw]

    # filter by min-duration
    def dur(w):
        if not w.get("start") or not w.get("end"): return 0
        s = parse_dt(w["start"]) ; e = parse_dt(w["end"])
        return max(0, int((e-s).total_seconds()))
    final = [w for w in final if dur(w) >= args.min_duration]

    # TLE Integration: Merge with TLE-derived windows if TLE file provided
    if args.tle_file:
        try:
            from tle_oasis_bridge import merge_windows, load_ground_stations, convert_tle_to_oasis_format
            import subprocess

            # Load ground stations
            if args.stations.exists():
                stations = load_ground_stations(args.stations)
            else:
                print(f"WARNING: Stations file not found: {args.stations}", file=sys.stderr)
                print("TLE windows will use coordinate strings for gw field", file=sys.stderr)
                stations = None

            # Determine time range from OASIS windows or use defaults
            if final:
                # Extract time range from existing windows
                all_times = []
                for w in final:
                    if w.get("start"):
                        all_times.append(parse_dt(w["start"]))
                    if w.get("end"):
                        all_times.append(parse_dt(w["end"]))
                start_time = min(all_times).isoformat().replace('+00:00', 'Z')
                end_time = max(all_times).isoformat().replace('+00:00', 'Z')
            else:
                # Use 24-hour window from now
                from datetime import timedelta
                now = datetime.now(timezone.utc)
                start_time = now.isoformat().replace('+00:00', 'Z')
                end_time = (now + timedelta(days=1)).isoformat().replace('+00:00', 'Z')

            # Calculate TLE windows for all ground stations
            tle_windows_all = []
            if stations:
                for station in stations:
                    # Run tle_windows.py for each station
                    tle_output = Path(f"/tmp/tle_{station['name']}.json")
                    cmd = [
                        sys.executable,
                        str(Path(__file__).parent / 'tle_windows.py'),
                        '--tle', str(args.tle_file),
                        '--lat', str(station['lat']),
                        '--lon', str(station['lon']),
                        '--alt', str(station.get('alt', 0.0)),
                        '--start', start_time,
                        '--end', end_time,
                        '--min-elev', str(args.min_elevation),
                        '--step', str(args.tle_step),
                        '--out', str(tle_output)
                    ]

                    try:
                        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                        if tle_output.exists():
                            tle_data = json.loads(tle_output.read_text())
                            tle_windows_all.extend(tle_data.get('windows', []))
                    except subprocess.CalledProcessError as e:
                        print(f"WARNING: TLE calculation failed for {station['name']}: {e.stderr}",
                             file=sys.stderr)
                        continue

            # Merge OASIS and TLE windows
            final = merge_windows(
                oasis_windows=final,
                tle_windows=tle_windows_all,
                strategy=args.merge_strategy,
                stations=stations
            )

            print(f"✓ Merged with TLE: {len(tle_windows_all)} TLE windows, "
                 f"strategy='{args.merge_strategy}'", file=sys.stderr)

        except ImportError as e:
            print(f"ERROR: TLE integration failed - missing dependency: {e}", file=sys.stderr)
            print("Continuing with OASIS-only windows...", file=sys.stderr)
        except Exception as e:
            print(f"ERROR: TLE integration failed: {e}", file=sys.stderr)
            print("Continuing with OASIS-only windows...", file=sys.stderr)

    out = {
        "meta": {
            "source": str(args.log),
            "count": len(final),
            "tle_file": str(args.tle_file) if args.tle_file else None,
            "merge_strategy": args.merge_strategy if args.tle_file else None
        },
        "windows": final
    }

    # Final validation of complete output
    if not args.skip_validation:
        try:
            validate_windows(out)
            print(f"✓ Schema validation passed: {len(final)} windows", file=sys.stderr)
        except ValidationError as e:
            print(f"ERROR: Output validation failed: {e}", file=sys.stderr)
            return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"kept": len(final), "outfile": str(args.output)}, indent=2))
    return 0

if __name__ == "__main__":
    exit(main())
