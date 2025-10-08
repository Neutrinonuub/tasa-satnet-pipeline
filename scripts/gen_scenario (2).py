#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def load_json(p: Path):
    return json.loads(p.read_text(encoding='utf-8')) if p and p.exists() else {'windows': []}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--oasis', type=Path, default=Path('data/oasis_windows.json'))
    ap.add_argument('--tle', type=Path, default=Path('data/tle_windows.json'))
    ap.add_argument('--out', type=Path, default=Path('config/ns3_scenario.json'))
    ap.add_argument('--relay', choices=['transparent','regenerative'], default='transparent')
    args = ap.parse_args()

    oasis = load_json(args.oasis); tle = load_json(args.tle)
    scenario = {'version':1,'relay_mode':args.relay,
                'satellites':[{'name':'SAT-1'}],
                'gateways':[{'name':'HSINCHU'},{'name':'TAIPEI'}],
                'user_beams':[{'name':'beam-1'}],
                'events': oasis.get('windows', []) + tle.get('windows', [])}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scenario, indent=2), encoding='utf-8')
    print(json.dumps({'outfile': str(args.out), 'events': len(scenario['events'])}, indent=2))

if __name__ == '__main__': main()
