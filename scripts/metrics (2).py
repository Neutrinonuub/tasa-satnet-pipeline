#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, csv
from datetime import datetime, timezone
from pathlib import Path

C = 299792.458  # km/s

def parse_dt(s: str):
    return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc).replace(tzinfo=timezone.utc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenario', type=Path, required=True)
    ap.add_argument('--out', type=Path, default=Path('reports/metrics.csv'))
    ap.add_argument('--link-rate-mbps', type=float, default=200.0)
    ap.add_argument('--duty', type=float, default=0.7)
    args = ap.parse_args()

    sc = json.loads(args.scenario.read_text(encoding='utf-8'))
    rows = []
    for ev in sc.get('events', []):
        if not ev.get('start') or not ev.get('end'): 
            continue
        t0, t1 = parse_dt(ev['start']), parse_dt(ev['end'])
        dur = (t1 - t0).total_seconds()
        sat_name = (ev.get('sat') or '').upper()
        slant_km = 1200.0 if 'ISS' in sat_name or 'LEO' in sat_name else 72000.0
        prop_s = slant_km / C
        thr_mb = args.link_rate_mbps * args.duty * dur / 8.0
        rows.append({'type': ev.get('type','?'), 'start': ev['start'], 'end': ev['end'],
                     'duration_s': int(dur), 'propagation_s': round(prop_s, 4), 'throughput_est_MB': round(thr_mb,1)})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with args.out.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['type','start','end','duration_s','propagation_s','throughput_est_MB'])
        w.writeheader()
        for r in rows: w.writerow(r)
    print(f"wrote {len(rows)} rows -> {args.out}")

if __name__ == '__main__': main()
