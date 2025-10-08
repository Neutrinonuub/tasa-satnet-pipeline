#!/usr/bin/env python3
"""Compute metrics and KPIs from NS-3 scenario."""
from __future__ import annotations
import json
import argparse
import csv
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import math


class MetricsCalculator:
    """Calculate network performance metrics."""
    
    SPEED_OF_LIGHT = 299792.458  # km/s
    
    def __init__(self, scenario: Dict):
        """Initialize with scenario data."""
        self.scenario = scenario
        self.mode = scenario.get('metadata', {}).get('mode', 'transparent')
        self.metrics: List[Dict] = []
    
    def compute_all_metrics(self) -> List[Dict]:
        """Compute all metrics for scenario."""
        events = self.scenario.get('events', [])
        parameters = self.scenario.get('parameters', {})
        
        # Group events into sessions (link_up to link_down pairs)
        sessions = self._extract_sessions(events)
        
        for session in sessions:
            metrics = self._compute_session_metrics(session, parameters)
            self.metrics.append(metrics)
        
        return self.metrics
    
    def _extract_sessions(self, events: List[Dict]) -> List[Dict]:
        """Extract communication sessions from events."""
        sessions = []
        active_links = {}
        
        for event in events:
            link_key = (event['source'], event['target'])
            
            if event['type'] == 'link_up':
                active_links[link_key] = {
                    'start': event['time'],
                    'source': event['source'],
                    'target': event['target'],
                    'window_type': event.get('window_type', 'unknown')
                }
            elif event['type'] == 'link_down':
                if link_key in active_links:
                    session = active_links[link_key]
                    session['end'] = event['time']
                    sessions.append(session)
                    del active_links[link_key]
        
        return sessions
    
    def _compute_session_metrics(self, session: Dict, parameters: Dict) -> Dict:
        """Compute metrics for a single session."""
        # Parse times
        start = datetime.fromisoformat(session['start'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(session['end'].replace('Z', '+00:00'))
        duration_sec = (end - start).total_seconds()
        
        # Latency components
        propagation_delay = self._compute_propagation_delay()
        processing_delay = parameters.get('processing_delay_ms', 0.0)
        queuing_delay = self._estimate_queuing_delay(duration_sec)
        transmission_delay = self._compute_transmission_delay(parameters)
        
        total_latency = propagation_delay + processing_delay + queuing_delay + transmission_delay
        
        # Throughput
        data_rate_mbps = parameters.get('data_rate_mbps', 50)
        throughput_mbps = self._compute_throughput(duration_sec, data_rate_mbps)
        
        return {
            'source': session['source'],
            'target': session['target'],
            'window_type': session['window_type'],
            'start': session['start'],
            'end': session['end'],
            'duration_sec': duration_sec,
            'latency': {
                'propagation_ms': round(propagation_delay, 2),
                'processing_ms': round(processing_delay, 2),
                'queuing_ms': round(queuing_delay, 2),
                'transmission_ms': round(transmission_delay, 2),
                'total_ms': round(total_latency, 2),
                'rtt_ms': round(total_latency * 2, 2)  # Round-trip time
            },
            'throughput': {
                'average_mbps': round(throughput_mbps, 2),
                'peak_mbps': data_rate_mbps,
                'utilization_percent': round(throughput_mbps / data_rate_mbps * 100, 2)
            },
            'mode': self.mode
        }
    
    def _compute_propagation_delay(self, altitude_km: float = 550) -> float:
        """Compute propagation delay for satellite link."""
        # Simplified: distance to satellite and back
        distance_km = altitude_km * 2  # Up and down
        delay_ms = (distance_km / self.SPEED_OF_LIGHT) * 1000
        return delay_ms
    
    def _estimate_queuing_delay(self, duration_sec: float) -> float:
        """Estimate queuing delay based on traffic patterns."""
        # Simplified model: assume higher queuing during longer sessions
        if duration_sec < 60:
            return 0.5  # Low traffic
        elif duration_sec < 300:
            return 2.0  # Medium traffic
        else:
            return 5.0  # High traffic
    
    def _compute_transmission_delay(self, parameters: Dict) -> float:
        """Compute transmission delay for packet."""
        packet_size_kb = 1.5  # MTU ~1500 bytes
        data_rate_mbps = parameters.get('data_rate_mbps', 50)
        delay_ms = (packet_size_kb * 8) / (data_rate_mbps * 1000) * 1000
        return delay_ms
    
    def _compute_throughput(self, duration_sec: float, data_rate_mbps: float) -> float:
        """Compute average throughput."""
        # Simplified: assume 80% utilization during active session
        return data_rate_mbps * 0.8
    
    def generate_summary(self) -> Dict:
        """Generate summary statistics."""
        if not self.metrics:
            return {}
        
        latencies = [m['latency']['total_ms'] for m in self.metrics]
        throughputs = [m['throughput']['average_mbps'] for m in self.metrics]
        
        return {
            'total_sessions': len(self.metrics),
            'mode': self.mode,
            'latency': {
                'mean_ms': round(sum(latencies) / len(latencies), 2),
                'min_ms': round(min(latencies), 2),
                'max_ms': round(max(latencies), 2),
                'p95_ms': round(self._percentile(latencies, 95), 2)
            },
            'throughput': {
                'mean_mbps': round(sum(throughputs) / len(throughputs), 2),
                'min_mbps': round(min(throughputs), 2),
                'max_mbps': round(max(throughputs), 2)
            },
            'total_duration_sec': sum(m['duration_sec'] for m in self.metrics)
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Compute percentile of data."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def export_csv(self, output_path: Path):
        """Export metrics to CSV."""
        if not self.metrics:
            return
        
        with output_path.open('w', newline='') as f:
            fieldnames = [
                'source', 'target', 'window_type', 'start', 'end', 'duration_sec',
                'latency_total_ms', 'latency_rtt_ms', 'throughput_mbps', 'utilization_percent', 'mode'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for m in self.metrics:
                writer.writerow({
                    'source': m['source'],
                    'target': m['target'],
                    'window_type': m['window_type'],
                    'start': m['start'],
                    'end': m['end'],
                    'duration_sec': m['duration_sec'],
                    'latency_total_ms': m['latency']['total_ms'],
                    'latency_rtt_ms': m['latency']['rtt_ms'],
                    'throughput_mbps': m['throughput']['average_mbps'],
                    'utilization_percent': m['throughput']['utilization_percent'],
                    'mode': m['mode']
                })


def main():
    """CLI interface for metrics calculation."""
    ap = argparse.ArgumentParser(description="Compute metrics from NS-3 scenario")
    ap.add_argument("scenario", type=Path, help="Scenario JSON file")
    ap.add_argument("-o", "--output", type=Path, default=Path("reports/metrics.csv"))
    ap.add_argument("--summary", type=Path, default=Path("reports/summary.json"))
    
    args = ap.parse_args()
    
    # Load scenario
    with args.scenario.open() as f:
        scenario = json.load(f)
    
    # Compute metrics
    calculator = MetricsCalculator(scenario)
    metrics = calculator.compute_all_metrics()
    summary = calculator.generate_summary()
    
    # Export
    args.output.parent.mkdir(parents=True, exist_ok=True)
    calculator.export_csv(args.output)
    
    args.summary.write_text(json.dumps(summary, indent=2))
    
    print(json.dumps({
        'metrics_computed': len(metrics),
        'mode': summary.get('mode'),
        'mean_latency_ms': summary.get('latency', {}).get('mean_ms'),
        'mean_throughput_mbps': summary.get('throughput', {}).get('mean_mbps'),
        'output_csv': str(args.output),
        'output_summary': str(args.summary)
    }, indent=2))
    
    return 0


if __name__ == "__main__":
    exit(main())
