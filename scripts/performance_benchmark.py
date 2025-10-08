#!/usr/bin/env python3
"""Performance benchmarking for TASA SatNet Pipeline."""
import time
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# Test datasets
BENCHMARKS = [
    {
        'name': 'Small (2 windows)',
        'input': 'data/windows_pipeline.json',
        'windows': 2,
        'satellites': 1,
        'description': 'Basic OASIS log parsing'
    },
    {
        'name': 'Medium (361 multi-const)',
        'input': 'data/multi_const_oasis.json',
        'windows': 361,
        'satellites': 84,
        'description': 'Multi-constellation (GPS/Iridium/OneWeb/Starlink)'
    },
    {
        'name': 'Large (1052 Starlink)',
        'input': 'data/scale_test_100sats_oasis.json',
        'windows': 1052,
        'satellites': 100,
        'description': '100 Starlink satellites, 12-hour period'
    }
]

def run_pipeline_stage(stage_name: str, command: List[str]) -> Dict:
    """Run a pipeline stage and measure performance."""
    start = time.time()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )
        elapsed = time.time() - start

        return {
            'stage': stage_name,
            'status': 'success' if result.returncode == 0 else 'failed',
            'time_sec': round(elapsed, 3),
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {
            'stage': stage_name,
            'status': 'timeout',
            'time_sec': round(elapsed, 3)
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            'stage': stage_name,
            'status': 'error',
            'time_sec': round(elapsed, 3),
            'error': str(e)
        }

def benchmark_dataset(benchmark: Dict) -> Dict:
    """Run complete pipeline benchmark for a dataset."""
    print(f"\n{'='*70}")
    print(f"Benchmarking: {benchmark['name']}")
    print(f"Description: {benchmark['description']}")
    print(f"Windows: {benchmark['windows']}, Satellites: {benchmark['satellites']}")
    print(f"{'='*70}\n")

    input_file = benchmark['input']
    results = []

    # Stage 1: Scenario Generation
    print("1. Scenario Generation...", end=' ', flush=True)
    scenario_file = f"/tmp/bench_scenario_{benchmark['windows']}.json"
    result = run_pipeline_stage(
        'scenario_generation',
        ['python', 'scripts/gen_scenario.py', input_file, '-o', scenario_file]
    )
    results.append(result)
    print(f"{result['status']} ({result['time_sec']}s)")

    if result['status'] != 'success':
        return {'benchmark': benchmark['name'], 'status': 'failed', 'results': results}

    # Stage 2: Metrics Calculation
    print("2. Metrics Calculation...", end=' ', flush=True)
    metrics_file = f"/tmp/bench_metrics_{benchmark['windows']}.csv"
    summary_file = f"/tmp/bench_summary_{benchmark['windows']}.json"
    result = run_pipeline_stage(
        'metrics_calculation',
        ['python', 'scripts/metrics.py', scenario_file, '-o', metrics_file, '--summary', summary_file]
    )
    results.append(result)
    print(f"{result['status']} ({result['time_sec']}s)")

    # Stage 3: Scheduling
    print("3. Beam Scheduling...", end=' ', flush=True)
    schedule_file = f"/tmp/bench_schedule_{benchmark['windows']}.csv"
    result = run_pipeline_stage(
        'beam_scheduling',
        ['python', 'scripts/scheduler.py', scenario_file, '-o', schedule_file]
    )
    results.append(result)
    print(f"{result['status']} ({result['time_sec']}s)")

    # Calculate totals
    total_time = sum(r['time_sec'] for r in results)
    throughput = benchmark['windows'] / total_time if total_time > 0 else 0

    print(f"\nTotal Time: {total_time:.3f}s")
    print(f"Throughput: {throughput:.1f} windows/sec\n")

    return {
        'benchmark': benchmark['name'],
        'input': benchmark['input'],
        'windows': benchmark['windows'],
        'satellites': benchmark['satellites'],
        'description': benchmark['description'],
        'status': 'completed',
        'stages': results,
        'total_time_sec': round(total_time, 3),
        'throughput_windows_per_sec': round(throughput, 1)
    }

def main():
    """Run all benchmarks and generate report."""
    print("\n" + "="*70)
    print("TASA SATNET PIPELINE - PERFORMANCE BENCHMARK")
    print("="*70)

    all_results = []

    for benchmark in BENCHMARKS:
        # Check if input file exists
        if not Path(benchmark['input']).exists():
            print(f"\n[SKIP] {benchmark['name']}: Input file not found")
            continue

        result = benchmark_dataset(benchmark)
        all_results.append(result)

    # Generate summary report
    print("\n" + "="*70)
    print("BENCHMARK SUMMARY")
    print("="*70 + "\n")

    print(f"{'Dataset':<30} {'Windows':<10} {'Time (s)':<12} {'Throughput':<15}")
    print("-" * 70)

    for result in all_results:
        if result['status'] == 'completed':
            print(f"{result['benchmark']:<30} "
                  f"{result['windows']:<10} "
                  f"{result['total_time_sec']:<12.3f} "
                  f"{result['throughput_windows_per_sec']:.1f} win/s")

    # Save detailed results
    output_file = Path('reports/performance_benchmark.json')
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'benchmarks': all_results
        }, f, indent=2)

    print(f"\n[OK] Detailed results saved to: {output_file}")
    print("="*70 + "\n")

    return 0

if __name__ == '__main__':
    sys.exit(main())
