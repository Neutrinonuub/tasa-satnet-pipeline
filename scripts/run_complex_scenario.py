#!/usr/bin/env python3
"""Run complex multi-satellite scenario testing."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_command(cmd: list[str], description: str) -> dict:
    """Run command and capture result."""
    print(f"\n{'='*60}")
    print(f"[*] {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("[OK] Success")
        try:
            return json.loads(result.stdout)
        except:
            return {'stdout': result.stdout}
    else:
        print(f"[ERROR] Error: {result.stderr}")
        return {'error': result.stderr}

def main():
    ap = argparse.ArgumentParser(description="Run complex scenario test")
    ap.add_argument('--log', type=Path,
                    default=Path('data/complex_oasis.log'),
                    help='Complex OASIS log file')
    ap.add_argument('--mode', choices=['transparent', 'regenerative'],
                    default='transparent',
                    help='Relay mode')
    ap.add_argument('--output-dir', type=Path,
                    default=Path('results/complex'),
                    help='Output directory')

    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Pipeline steps
    steps = []

    # Step 1: Parse complex log
    windows_file = args.output_dir / 'windows.json'
    steps.append(run_command([
        sys.executable, 'scripts/parse_oasis_log.py',
        str(args.log),
        '-o', str(windows_file)
    ], "Step 1: Parse Complex OASIS Log"))

    # Step 2: Generate scenario
    scenario_file = args.output_dir / f'scenario_{args.mode}.json'
    steps.append(run_command([
        sys.executable, 'scripts/gen_scenario.py',
        str(windows_file),
        '-o', str(scenario_file),
        '--mode', args.mode
    ], f"Step 2: Generate {args.mode.capitalize()} Scenario"))

    # Step 3: Calculate metrics
    metrics_file = args.output_dir / f'metrics_{args.mode}.csv'
    summary_file = args.output_dir / f'summary_{args.mode}.json'
    steps.append(run_command([
        sys.executable, 'scripts/metrics.py',
        str(scenario_file),
        '-o', str(metrics_file),
        '--summary', str(summary_file)
    ], "Step 3: Calculate Metrics"))

    # Step 4: Schedule beams
    schedule_file = args.output_dir / f'schedule_{args.mode}.csv'
    stats_file = args.output_dir / f'schedule_stats_{args.mode}.json'
    steps.append(run_command([
        sys.executable, 'scripts/scheduler.py',
        str(scenario_file),
        '-o', str(schedule_file),
        '--stats', str(stats_file),
        '--capacity', '8'
    ], "Step 4: Schedule Beams"))

    # Summary
    print(f"\n{'='*60}")
    print("COMPLEX SCENARIO TEST SUMMARY")
    print(f"{'='*60}")

    print(f"\nMode: {args.mode.upper()}")
    print(f"Log: {args.log}")
    print(f"Output: {args.output_dir}/")

    # Load and display key metrics
    if summary_file.exists():
        with summary_file.open() as f:
            summary = json.load(f)

        print(f"\nKey Metrics:")
        print(f"  Sessions: {summary.get('total_sessions', 'N/A')}")
        print(f"  Mean Latency: {summary.get('latency', {}).get('mean_ms', 'N/A')} ms")
        print(f"  Mean Throughput: {summary.get('throughput', {}).get('mean_mbps', 'N/A')} Mbps")

    if stats_file.exists():
        with stats_file.open() as f:
            stats = json.load(f)

        print(f"\nScheduling:")
        print(f"  Scheduled: {stats.get('scheduled', 'N/A')}")
        print(f"  Conflicts: {stats.get('conflicts', 'N/A')}")
        print(f"  Success Rate: {stats.get('success_rate', 'N/A')}%")

    print(f"\n[OK] Complex scenario test complete!")
    print(f"Results saved to: {args.output_dir}/")

    return 0

if __name__ == '__main__':
    exit(main())
