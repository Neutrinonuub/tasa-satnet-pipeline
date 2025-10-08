#!/usr/bin/env python3
"""Beam scheduler for satellite communications."""
from __future__ import annotations
import json
import argparse
import csv
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class TimeSlot:
    """Time slot for scheduling."""
    start: datetime
    end: datetime
    satellite: str
    gateway: str
    window_type: str
    assigned: bool = False


class BeamScheduler:
    """Schedule beam allocations to avoid conflicts."""
    
    def __init__(self, capacity_per_gateway: int = 4):
        """Initialize scheduler."""
        self.capacity_per_gateway = capacity_per_gateway
        self.schedule: List[TimeSlot] = []
        self.conflicts: List[Dict] = []
    
    def schedule_windows(self, scenario: Dict) -> List[TimeSlot]:
        """Schedule all windows from scenario."""
        events = scenario.get('events', [])
        
        # Extract time slots
        slots = self._extract_time_slots(events)
        
        # Sort by start time
        slots.sort(key=lambda s: s.start)
        
        # Greedy scheduling
        for slot in slots:
            if self._can_assign(slot):
                slot.assigned = True
                self.schedule.append(slot)
            else:
                self.conflicts.append({
                    'satellite': slot.satellite,
                    'gateway': slot.gateway,
                    'start': slot.start.isoformat(),
                    'end': slot.end.isoformat(),
                    'reason': 'capacity_exceeded'
                })
        
        return self.schedule
    
    def _extract_time_slots(self, events: List[Dict]) -> List[TimeSlot]:
        """Extract time slots from events."""
        slots = []
        active_sessions = {}
        
        for event in events:
            key = (event['source'], event['target'])
            
            if event['type'] == 'link_up':
                active_sessions[key] = {
                    'start': datetime.fromisoformat(event['time'].replace('Z', '+00:00')),
                    'satellite': event['source'],
                    'gateway': event['target'],
                    'window_type': event.get('window_type', 'unknown')
                }
            elif event['type'] == 'link_down' and key in active_sessions:
                session = active_sessions[key]
                slots.append(TimeSlot(
                    start=session['start'],
                    end=datetime.fromisoformat(event['time'].replace('Z', '+00:00')),
                    satellite=session['satellite'],
                    gateway=session['gateway'],
                    window_type=session['window_type']
                ))
                del active_sessions[key]
        
        return slots
    
    def _can_assign(self, new_slot: TimeSlot) -> bool:
        """Check if slot can be assigned without conflicts."""
        # Count concurrent sessions for this gateway
        concurrent = 0
        
        for slot in self.schedule:
            if slot.gateway != new_slot.gateway:
                continue
            
            # Check for overlap
            if self._overlaps(slot, new_slot):
                concurrent += 1
        
        return concurrent < self.capacity_per_gateway
    
    def _overlaps(self, slot1: TimeSlot, slot2: TimeSlot) -> bool:
        """Check if two time slots overlap."""
        return not (slot1.end <= slot2.start or slot2.end <= slot1.start)
    
    def compute_statistics(self) -> Dict:
        """Compute scheduling statistics."""
        total_slots = len(self.schedule) + len(self.conflicts)
        
        if total_slots == 0:
            return {'status': 'no_slots'}
        
        # Utilization per gateway
        gateway_usage = {}
        for slot in self.schedule:
            if slot.gateway not in gateway_usage:
                gateway_usage[slot.gateway] = 0
            duration = (slot.end - slot.start).total_seconds()
            gateway_usage[slot.gateway] += duration
        
        return {
            'total_slots': total_slots,
            'scheduled': len(self.schedule),
            'conflicts': len(self.conflicts),
            'success_rate': round(len(self.schedule) / total_slots * 100, 2),
            'gateways': len(gateway_usage),
            'gateway_usage_sec': gateway_usage,
            'capacity_per_gateway': self.capacity_per_gateway
        }
    
    def export_schedule(self, output_path: Path):
        """Export schedule to CSV."""
        with output_path.open('w', newline='') as f:
            fieldnames = ['satellite', 'gateway', 'start', 'end', 'duration_sec', 'window_type', 'assigned']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            all_slots = self.schedule + [
                TimeSlot(
                    start=datetime.fromisoformat(c['start'].replace('Z', '+00:00')),
                    end=datetime.fromisoformat(c['end'].replace('Z', '+00:00')),
                    satellite=c['satellite'],
                    gateway=c['gateway'],
                    window_type='unknown',
                    assigned=False
                )
                for c in self.conflicts
            ]
            
            for slot in sorted(all_slots, key=lambda s: s.start):
                writer.writerow({
                    'satellite': slot.satellite,
                    'gateway': slot.gateway,
                    'start': slot.start.isoformat(),
                    'end': slot.end.isoformat(),
                    'duration_sec': int((slot.end - slot.start).total_seconds()),
                    'window_type': slot.window_type,
                    'assigned': 'yes' if slot.assigned else 'no'
                })


def main():
    """CLI interface for beam scheduling."""
    ap = argparse.ArgumentParser(description="Schedule beam allocations")
    ap.add_argument("scenario", type=Path, help="Scenario JSON file")
    ap.add_argument("-o", "--output", type=Path, default=Path("reports/schedule.csv"))
    ap.add_argument("--capacity", type=int, default=4, help="Beams per gateway")
    ap.add_argument("--stats", type=Path, default=Path("reports/schedule_stats.json"))
    
    args = ap.parse_args()
    
    # Load scenario
    with args.scenario.open() as f:
        scenario = json.load(f)
    
    # Schedule
    scheduler = BeamScheduler(capacity_per_gateway=args.capacity)
    schedule = scheduler.schedule_windows(scenario)
    stats = scheduler.compute_statistics()
    
    # Export
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scheduler.export_schedule(args.output)
    
    args.stats.write_text(json.dumps(stats, indent=2))
    
    print(json.dumps({
        'scheduled': len(schedule),
        'conflicts': len(scheduler.conflicts),
        'success_rate': stats.get('success_rate', 0),
        'output': str(args.output),
        'stats': str(args.stats)
    }, indent=2))
    
    return 0


if __name__ == "__main__":
    exit(main())
