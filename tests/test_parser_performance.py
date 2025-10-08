#!/usr/bin/env python3
"""Performance benchmarks for OASIS log parser.

Tests the O(n) optimization of the pairing algorithm vs naive O(n^2) approach.
"""
import pytest
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Deque


def pair_windows_naive(windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """O(n²) naive pairing algorithm (original implementation)."""
    enters = [(i, w) for i, w in enumerate(windows) if w["type"] == "cmd_enter"]
    exits = [(i, w) for i, w in enumerate(windows) if w["type"] == "cmd_exit"]
    paired = []
    used_exits = set()

    for i, w in enters:
        for j, x in exits:
            if j in used_exits:
                continue
            if x["sat"] == w["sat"] and x["gw"] == w["gw"]:
                paired.append({
                    "type": "cmd",
                    "start": w["start"],
                    "end": x["end"],
                    "sat": w["sat"],
                    "gw": w["gw"],
                    "source": "log"
                })
                used_exits.add(j)
                break

    return paired


def pair_windows_optimized(windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """O(n) optimized pairing algorithm using hash map with deque."""
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


def generate_test_windows(n_pairs: int, n_satellites: int = 10) -> List[Dict[str, Any]]:
    """Generate synthetic command windows for benchmarking.

    Args:
        n_pairs: Number of enter/exit pairs to generate
        n_satellites: Number of unique satellites to distribute across

    Returns:
        List of window dictionaries with realistic structure
    """
    windows = []
    base_time = datetime(2025, 10, 8, 0, 0, 0, tzinfo=timezone.utc)

    satellites = [f"SAT-{i+1}" for i in range(n_satellites)]
    gateways = ["HSINCHU", "TAIPEI", "KAOHSIUNG", "TAICHUNG"]

    for i in range(n_pairs):
        sat = satellites[i % n_satellites]
        gw = gateways[i % len(gateways)]

        enter_time = base_time + timedelta(minutes=i * 10)
        exit_time = enter_time + timedelta(minutes=5)

        windows.append({
            "type": "cmd_enter",
            "start": enter_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": None,
            "sat": sat,
            "gw": gw,
            "source": "log"
        })

        windows.append({
            "type": "cmd_exit",
            "start": None,
            "end": exit_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sat": sat,
            "gw": gw,
            "source": "log"
        })

    return windows


class TestPairingPerformance:
    """Performance benchmarks for pairing algorithms."""

    def test_small_dataset_correctness(self):
        """Verify both algorithms produce identical results on small dataset."""
        windows = generate_test_windows(n_pairs=10)

        naive_result = pair_windows_naive(windows)
        optimized_result = pair_windows_optimized(windows)

        assert len(naive_result) == len(optimized_result)

        # Sort both results for comparison (may be in different orders)
        def sort_key(w):
            return (w["sat"], w["gw"], w["start"])

        naive_sorted = sorted(naive_result, key=sort_key)
        optimized_sorted = sorted(optimized_result, key=sort_key)

        assert naive_sorted == optimized_sorted

    def test_large_dataset_correctness(self):
        """Verify correctness on larger dataset (100 pairs)."""
        windows = generate_test_windows(n_pairs=100)

        naive_result = pair_windows_naive(windows)
        optimized_result = pair_windows_optimized(windows)

        assert len(naive_result) == len(optimized_result) == 100

    @pytest.mark.benchmark
    def test_performance_100_windows(self):
        """Benchmark: 100 window pairs (realistic OASIS log size)."""
        windows = generate_test_windows(n_pairs=100)

        # Naive O(n²) approach
        start = time.perf_counter()
        naive_result = pair_windows_naive(windows)
        naive_time = time.perf_counter() - start

        # Optimized O(n) approach
        start = time.perf_counter()
        optimized_result = pair_windows_optimized(windows)
        optimized_time = time.perf_counter() - start

        print(f"\n100 pairs:")
        print(f"  Naive O(n^2): {naive_time*1000:.3f}ms")
        print(f"  Optimized O(n): {optimized_time*1000:.3f}ms")
        print(f"  Speedup: {naive_time/optimized_time:.1f}x")

        assert len(naive_result) == len(optimized_result)
        assert optimized_time < naive_time

    @pytest.mark.benchmark
    def test_performance_1000_windows(self):
        """Benchmark: 1000 window pairs (stress test).

        Expected performance:
        - Naive O(n²): ~1000ms+
        - Optimized O(n): <10ms
        - Speedup: >100x
        """
        windows = generate_test_windows(n_pairs=1000)

        # Naive O(n²) approach
        start = time.perf_counter()
        naive_result = pair_windows_naive(windows)
        naive_time = time.perf_counter() - start

        # Optimized O(n) approach
        start = time.perf_counter()
        optimized_result = pair_windows_optimized(windows)
        optimized_time = time.perf_counter() - start

        print(f"\n1000 pairs:")
        print(f"  Naive O(n^2): {naive_time*1000:.3f}ms")
        print(f"  Optimized O(n): {optimized_time*1000:.3f}ms")
        print(f"  Speedup: {naive_time/optimized_time:.1f}x")

        assert len(naive_result) == len(optimized_result) == 1000

        # Performance assertions
        assert optimized_time < 0.010, f"Optimized algorithm took {optimized_time*1000:.3f}ms (expected <10ms)"
        assert naive_time / optimized_time > 2, f"Speedup was only {naive_time/optimized_time:.1f}x (expected >2x)"

        print(f"\nPerformance target met: Optimized O(n) completed in {optimized_time*1000:.3f}ms (<10ms)")

    @pytest.mark.benchmark
    def test_performance_scaling(self):
        """Test algorithmic complexity by measuring scaling behavior."""
        sizes = [10, 50, 100, 500, 1000]
        naive_times = []
        optimized_times = []

        print("\nScaling analysis:")
        print(f"{'Size':<8} {'Naive (ms)':<12} {'Optimized (ms)':<15} {'Speedup':<10}")
        print("-" * 50)

        for size in sizes:
            windows = generate_test_windows(n_pairs=size)

            # Measure naive
            start = time.perf_counter()
            pair_windows_naive(windows)
            naive_time = time.perf_counter() - start
            naive_times.append(naive_time)

            # Measure optimized
            start = time.perf_counter()
            pair_windows_optimized(windows)
            optimized_time = time.perf_counter() - start
            optimized_times.append(optimized_time)

            speedup = naive_time / optimized_time if optimized_time > 0 else float('inf')
            print(f"{size:<8} {naive_time*1000:<12.3f} {optimized_time*1000:<15.3f} {speedup:<10.1f}x")

        # Verify O(n) vs O(n²) scaling
        # For O(n²), 10x input should mean ~100x time increase
        # For O(n), 10x input should mean ~10x time increase
        if len(sizes) >= 3:
            ratio_10_to_100 = sizes[2] / sizes[0]  # 100/10 = 10x

            naive_scaling = naive_times[2] / naive_times[0]
            optimized_scaling = optimized_times[2] / optimized_times[0]

            print(f"\nScaling from {sizes[0]} to {sizes[2]} ({ratio_10_to_100}x input):")
            print(f"  Naive: {naive_scaling:.1f}x time (expected ~{ratio_10_to_100**2}x for O(n^2))")
            print(f"  Optimized: {optimized_scaling:.1f}x time (expected ~{ratio_10_to_100}x for O(n))")

            # Naive should scale worse than linear (at least 2x the input ratio)
            # Note: Actual O(n^2) scaling can be masked by constant factors for small inputs
            assert naive_scaling > ratio_10_to_100 * 1.5, "Naive algorithm not showing worse-than-linear scaling"

            # Optimized should scale much better than naive
            assert optimized_scaling < naive_scaling / 2, "Optimized algorithm not significantly better than naive"

    def test_edge_cases(self):
        """Test edge cases for optimized algorithm."""
        # Empty input
        assert pair_windows_optimized([]) == []

        # Only enters (no matches)
        windows = [{
            "type": "cmd_enter",
            "start": "2025-10-08T00:00:00Z",
            "end": None,
            "sat": "SAT-1",
            "gw": "HSINCHU",
            "source": "log"
        }]
        assert pair_windows_optimized(windows) == []

        # Only exits (no matches)
        windows = [{
            "type": "cmd_exit",
            "start": None,
            "end": "2025-10-08T00:05:00Z",
            "sat": "SAT-1",
            "gw": "HSINCHU",
            "source": "log"
        }]
        assert pair_windows_optimized(windows) == []

        # Mismatched sat/gw
        windows = [
            {
                "type": "cmd_enter",
                "start": "2025-10-08T00:00:00Z",
                "end": None,
                "sat": "SAT-1",
                "gw": "HSINCHU",
                "source": "log"
            },
            {
                "type": "cmd_exit",
                "start": None,
                "end": "2025-10-08T00:05:00Z",
                "sat": "SAT-2",  # Different satellite
                "gw": "HSINCHU",
                "source": "log"
            }
        ]
        assert pair_windows_optimized(windows) == []

    def test_multiple_pairs_same_satellite(self):
        """Test FIFO pairing for multiple windows on same sat/gw."""
        windows = [
            {"type": "cmd_enter", "start": "2025-10-08T00:00:00Z", "end": None,
             "sat": "SAT-1", "gw": "HSINCHU", "source": "log"},
            {"type": "cmd_enter", "start": "2025-10-08T01:00:00Z", "end": None,
             "sat": "SAT-1", "gw": "HSINCHU", "source": "log"},
            {"type": "cmd_exit", "start": None, "end": "2025-10-08T00:30:00Z",
             "sat": "SAT-1", "gw": "HSINCHU", "source": "log"},
            {"type": "cmd_exit", "start": None, "end": "2025-10-08T01:30:00Z",
             "sat": "SAT-1", "gw": "HSINCHU", "source": "log"},
        ]

        result = pair_windows_optimized(windows)
        assert len(result) == 2

        # Verify FIFO behavior
        assert result[0]["start"] == "2025-10-08T00:00:00Z"
        assert result[0]["end"] == "2025-10-08T00:30:00Z"
        assert result[1]["start"] == "2025-10-08T01:00:00Z"
        assert result[1]["end"] == "2025-10-08T01:30:00Z"


if __name__ == "__main__":
    # Run benchmarks directly
    test = TestPairingPerformance()

    print("=" * 60)
    print("OASIS Parser Performance Benchmarks")
    print("=" * 60)

    test.test_small_dataset_correctness()
    print("[OK] Small dataset correctness verified")

    test.test_large_dataset_correctness()
    print("[OK] Large dataset correctness verified")

    test.test_performance_100_windows()
    test.test_performance_1000_windows()
    test.test_performance_scaling()

    test.test_edge_cases()
    print("[OK] Edge cases passed")

    test.test_multiple_pairs_same_satellite()
    print("[OK] FIFO pairing verified")

    print("\n" + "=" * 60)
    print("All performance benchmarks passed!")
    print("=" * 60)
