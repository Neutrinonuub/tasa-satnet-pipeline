#!/usr/bin/env python3
"""Verify real deployment and data processing."""
import json
import csv
from pathlib import Path
from datetime import datetime


def verify_parser_output():
    """Verify parser produces real data."""
    print("\n=== VERIFYING PARSER ===")
    
    path = Path("data/oasis_windows.json")
    if not path.exists():
        print("❌ Parser output not found")
        return False
    
    with open(path) as f:
        data = json.load(f)
    
    # Check structure
    assert "meta" in data, "Missing meta"
    assert "windows" in data, "Missing windows"
    assert len(data["windows"]) > 0, "No windows parsed"
    
    # Check real data
    for w in data["windows"]:
        assert "start" in w or "end" in w, "Missing timestamps"
        assert "sat" in w, "Missing satellite"
        assert "gw" in w, "Missing gateway"
        assert w["type"] in ["cmd", "xband"], "Invalid type"
    
    print(f"[OK] Parser: {len(data['windows'])} windows")
    print(f"   Satellites: {set(w['sat'] for w in data['windows'])}")
    print(f"   Gateways: {set(w['gw'] for w in data['windows'])}")
    
    return True


def verify_scenario_output():
    """Verify scenario generator produces real topology."""
    print("\n=== VERIFYING SCENARIO GENERATOR ===")
    
    path = Path("config/ns3_scenario.json")
    if not path.exists():
        print("❌ Scenario output not found")
        return False
    
    with open(path) as f:
        data = json.load(f)
    
    # Check structure
    assert "metadata" in data, "Missing metadata"
    assert "topology" in data, "Missing topology"
    assert "events" in data, "Missing events"
    assert "parameters" in data, "Missing parameters"
    
    # Check real topology
    topo = data["topology"]
    assert len(topo["satellites"]) > 0, "No satellites"
    assert len(topo["gateways"]) > 0, "No gateways"
    assert len(topo["links"]) > 0, "No links"
    
    # Check events are time-ordered
    events = data["events"]
    times = [datetime.fromisoformat(e["time"].replace('Z', '+00:00')) for e in events]
    assert times == sorted(times), "Events not chronologically ordered"
    
    print(f"✅ Scenario: {data['metadata']['mode']} mode")
    print(f"   Satellites: {len(topo['satellites'])}")
    print(f"   Gateways: {len(topo['gateways'])}")
    print(f"   Links: {len(topo['links'])}")
    print(f"   Events: {len(events)}")
    
    return True


def verify_metrics_calculation():
    """Verify metrics are really computed."""
    print("\n=== VERIFYING METRICS CALCULATOR ===")
    
    # Check CSV output
    csv_path = Path("reports/metrics.csv")
    if not csv_path.exists():
        print("❌ Metrics CSV not found")
        return False
    
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert len(rows) > 0, "No metrics computed"
    
    # Check real calculations
    for row in rows:
        latency = float(row["latency_total_ms"])
        rtt = float(row["latency_rtt_ms"])
        throughput = float(row["throughput_mbps"])
        
        assert latency > 0, "Invalid latency"
        assert rtt >= latency * 2, "RTT should be >= 2x one-way"
        assert 0 < throughput <= 50, "Throughput out of range"
    
    # Check summary
    summary_path = Path("reports/summary.json")
    with open(summary_path) as f:
        summary = json.load(f)
    
    assert summary["total_sessions"] == len(rows), "Session count mismatch"
    
    print(f"✅ Metrics: {len(rows)} sessions computed")
    print(f"   Mean latency: {summary['latency']['mean_ms']}ms")
    print(f"   Mean throughput: {summary['throughput']['mean_mbps']}Mbps")
    print(f"   Mode: {summary['mode']}")
    
    return True


def verify_scheduler_logic():
    """Verify scheduler performs real conflict detection."""
    print("\n=== VERIFYING SCHEDULER ===")
    
    stats_path = Path("reports/schedule_stats.json")
    if not stats_path.exists():
        print("❌ Schedule stats not found")
        return False
    
    with open(stats_path) as f:
        stats = json.load(f)
    
    # Check real scheduling
    assert stats["total_slots"] > 0, "No slots to schedule"
    assert stats["scheduled"] <= stats["total_slots"], "Invalid schedule count"
    assert stats["conflicts"] >= 0, "Invalid conflict count"
    assert stats["scheduled"] + stats["conflicts"] == stats["total_slots"], "Count mismatch"
    
    # Check gateway usage
    assert "gateway_usage_sec" in stats, "Missing gateway usage"
    assert len(stats["gateway_usage_sec"]) > 0, "No gateway usage recorded"
    
    print(f"✅ Scheduler: {stats['scheduled']}/{stats['total_slots']} scheduled")
    print(f"   Conflicts: {stats['conflicts']}")
    print(f"   Success rate: {stats['success_rate']}%")
    print(f"   Gateway usage: {stats['gateway_usage_sec']}")
    
    return True


def verify_mode_comparison():
    """Verify transparent vs regenerative modes produce different results."""
    print("\n=== VERIFYING MODE COMPARISON ===")
    
    trans_path = Path("reports/trans_summary.json")
    regen_path = Path("reports/regen_summary.json")
    
    if not trans_path.exists() or not regen_path.exists():
        print("❌ Mode comparison files not found")
        return False
    
    with open(trans_path) as f:
        trans = json.load(f)
    
    with open(regen_path) as f:
        regen = json.load(f)
    
    # Modes must be different
    assert trans["mode"] == "transparent", "Wrong mode"
    assert regen["mode"] == "regenerative", "Wrong mode"
    
    # Regenerative should have higher latency (processing delay)
    trans_latency = trans["latency"]["mean_ms"]
    regen_latency = regen["latency"]["mean_ms"]
    
    assert regen_latency > trans_latency, "Regenerative should have higher latency"
    
    diff = regen_latency - trans_latency
    assert 4 < diff < 6, f"Processing delay should be ~5ms, got {diff}ms"
    
    print(f"✅ Mode Comparison:")
    print(f"   Transparent latency: {trans_latency}ms")
    print(f"   Regenerative latency: {regen_latency}ms")
    print(f"   Difference: {diff}ms (processing delay)")
    print(f"   ✓ Regenerative correctly adds processing delay")
    
    return True


def verify_data_flow():
    """Verify data flows correctly through pipeline."""
    print("\n=== VERIFYING DATA FLOW ===")
    
    # Load all pipeline outputs
    windows = json.load(open("data/oasis_windows.json"))
    scenario = json.load(open("config/ns3_scenario.json"))
    summary = json.load(open("reports/summary.json"))
    
    # Check data consistency
    num_windows = len(windows["windows"])
    num_events = len(scenario["events"])
    num_sessions = summary["total_sessions"]
    
    # Each window should produce 2 events (link_up, link_down)
    assert num_events == num_windows * 2, f"Event count mismatch: {num_events} != {num_windows} * 2"
    
    # Number of sessions should match number of windows
    assert num_sessions == num_windows, f"Session count mismatch: {num_sessions} != {num_windows}"
    
    # Check satellites/gateways match
    sats_in_windows = set(w["sat"] for w in windows["windows"])
    sats_in_scenario = set(s["id"] for s in scenario["topology"]["satellites"])
    assert sats_in_windows == sats_in_scenario, "Satellite mismatch"
    
    gws_in_windows = set(w["gw"] for w in windows["windows"])
    gws_in_scenario = set(g["id"] for g in scenario["topology"]["gateways"])
    assert gws_in_windows == gws_in_scenario, "Gateway mismatch"
    
    print(f"✅ Data Flow:")
    print(f"   Windows: {num_windows}")
    print(f"   Events: {num_events} (2 per window)")
    print(f"   Sessions: {num_sessions}")
    print(f"   Satellites: {sats_in_windows}")
    print(f"   Gateways: {gws_in_windows}")
    print(f"   ✓ Data flows correctly through pipeline")
    
    return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("REAL DEPLOYMENT VERIFICATION")
    print("=" * 60)
    
    tests = [
        ("Parser", verify_parser_output),
        ("Scenario Generator", verify_scenario_output),
        ("Metrics Calculator", verify_metrics_calculation),
        ("Scheduler", verify_scheduler_logic),
        ("Mode Comparison", verify_mode_comparison),
        ("Data Flow", verify_data_flow),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except AssertionError as e:
            print(f"❌ {name} FAILED: {e}")
            results.append((name, False))
        except Exception as e:
            print(f"❌ {name} ERROR: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL VERIFICATIONS PASSED - REAL IMPLEMENTATION CONFIRMED")
        return 0
    else:
        print("\n⚠️ SOME VERIFICATIONS FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
