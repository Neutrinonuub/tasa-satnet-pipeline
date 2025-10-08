#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

TS = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
PAT_ENTER = re.compile(rf"enter command window\s*@\s*({TS})\s*sat=(\S+)\s*gw=(\S+)", re.I)
PAT_EXIT  = re.compile(rf"exit command window\s*@\s*({TS})\s*sat=(\S+)\s*gw=(\S+)", re.I)
PAT_XBAND = re.compile(rf"X-band\s*data\s*link\s*window\s*:\s*({TS})\.{2}({TS})\s*sat=(\S+)\s*gw=(\S+)", re.I)

def parse_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("data/oasis_windows.json"))
    args = ap.parse_args()

    windows = []
    content = args.log.read_text(encoding="utf-8", errors="ignore")
    for m in PAT_ENTER.finditer(content):
        t, sat, gw = m.groups()
        windows.append({"type":"cmd_enter", "start": t, "end": None, "sat": sat, "gw": gw, "source":"log"})
    for m in PAT_EXIT.finditer(content):
        t, sat, gw = m.groups()
        windows.append({"type":"cmd_exit", "start": None, "end": t, "sat": sat, "gw": gw, "source":"log"})
    for m in PAT_XBAND.finditer(content):
        s, e, sat, gw = m.groups()
        windows.append({"type":"xband", "start": s, "end": e, "sat": sat, "gw": gw, "source":"log"})

    enters = [(i,w) for i,w in enumerate(windows) if w["type"]=="cmd_enter"]
    exits  = [(i,w) for i,w in enumerate(windows) if w["type"]=="cmd_exit"]
    paired, used = [], set()
    for i, w in enters:
        for j, x in exits:
            if j in used: continue
            if x["sat"]==w["sat"] and x["gw"]==w["gw"]:
                paired.append({"type":"cmd", "start": w["start"], "end": x["end"], "sat": w["sat"], "gw": w["gw"], "source":"log"})
                used.add(j); break

    final = [w for w in windows if w["type"]=="xband"] + paired
    out = {"meta": {"source": str(args.log), "count": len(final)}, "windows": final}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"kept": len(final), "outfile": str(args.output)}, indent=2))

if __name__ == "__main__": main()
