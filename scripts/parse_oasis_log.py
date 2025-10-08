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
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

TS = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"

PAT_ENTER = re.compile(rf"enter\s+command\s+window\s*@\s*({TS})\s*sat=(\S+)\s*gw=(\S+)", re.I)
PAT_EXIT  = re.compile(rf"exit\s+command\s+window\s*@\s*({TS})\s*sat=(\S+)\s*gw=(\S+)", re.I)
PAT_XBAND = re.compile(rf"X-band\s+data\s+link\s+window\s*:\s*({TS})\s*\.\.\s*({TS})\s*sat=(\S+)\s*gw=(\S+)", re.I)

def parse_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("data/oasis_windows.json"))
    ap.add_argument("--tz", default="UTC")
    ap.add_argument("--sat", default=None)
    ap.add_argument("--gw", default=None)
    ap.add_argument("--min-duration", type=int, default=0, help="min window seconds to keep")
    args = ap.parse_args()

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
        windows.append({"type":"xband", "start": s, "end": e, "sat": sat, "gw": gw, "source":"log"})

    # naive pairing for command windows (cmd_enter + cmd_exit per sat/gw FIFO)
    enters = [(i,w) for i,w in enumerate(windows) if w["type"]=="cmd_enter"]
    exits  = [(i,w) for i,w in enumerate(windows) if w["type"]=="cmd_exit"]
    paired = []
    used_exits = set()
    for i, w in enters:
        for j, x in exits:
            if j in used_exits: 
                continue
            if x["sat"]==w["sat"] and x["gw"]==w["gw"]:
                paired.append({"type":"cmd", "start": w["start"], "end": x["end"], "sat": w["sat"], "gw": w["gw"], "source":"log"})
                used_exits.add(j)
                break

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

    out = {
        "meta": {"source": str(args.log), "count": len(final)},
        "windows": final
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"kept": len(final), "outfile": str(args.output)}, indent=2))

if __name__ == "__main__":
    main()
