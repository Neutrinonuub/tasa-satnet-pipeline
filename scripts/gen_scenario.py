#!/usr/bin/env python3
"""Generate NS-3/SNS3 scenario from parsed OASIS windows."""
from __future__ import annotations
import json
import argparse
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime, timezone


class ScenarioGenerator:
    """Generate simulation scenario from parsed windows."""
    
    def __init__(self, mode: str = "transparent"):
        """Initialize generator with relay mode."""
        self.mode = mode  # transparent or regenerative
        self.satellites: Set[str] = set()
        self.gateways: Set[str] = set()
        self.links: List[Dict] = []
        self.events: List[Dict] = []
    
    def generate(self, windows_data: Dict) -> Dict:
        """Generate scenario from windows JSON."""
        windows = windows_data.get('windows', [])
        
        # Extract nodes
        for window in windows:
            self.satellites.add(window['sat'])
            self.gateways.add(window['gw'])
        
        # Generate topology
        topology = self._build_topology()
        
        # Generate events
        self._generate_events(windows)
        
        # Build scenario
        scenario = {
            'metadata': {
                'name': f"OASIS Scenario - {self.mode}",
                'mode': self.mode,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'source': windows_data.get('meta', {}).get('source', 'unknown')
            },
            'topology': topology,
            'events': self.events,
            'parameters': self._get_parameters()
        }
        
        return scenario
    
    def _build_topology(self) -> Dict:
        """Build network topology."""
        satellites = [
            {
                'id': sat,
                'type': 'satellite',
                'orbit': 'LEO',  # Default
                'altitude_km': 550,  # Default
            }
            for sat in sorted(self.satellites)
        ]
        
        gateways = [
            {
                'id': gw,
                'type': 'gateway',
                'location': gw,  # Use name as location
                'capacity_mbps': 100
            }
            for gw in sorted(self.gateways)
        ]
        
        # Generate links between all sats and gateways
        links = []
        for sat in self.satellites:
            for gw in self.gateways:
                links.append({
                    'source': sat,
                    'target': gw,
                    'type': 'sat-ground',
                    'bandwidth_mbps': 50,
                    'latency_ms': self._compute_base_latency()
                })
        
        return {
            'satellites': satellites,
            'gateways': gateways,
            'links': links
        }
    
    def _generate_events(self, windows: List[Dict]):
        """Generate timed events from windows."""
        for window in windows:
            start_time = datetime.fromisoformat(window['start'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(window['end'].replace('Z', '+00:00'))
            
            # Link up event
            self.events.append({
                'time': start_time.isoformat(),
                'type': 'link_up',
                'source': window['sat'],
                'target': window['gw'],
                'window_type': window['type']
            })
            
            # Link down event
            self.events.append({
                'time': end_time.isoformat(),
                'type': 'link_down',
                'source': window['sat'],
                'target': window['gw'],
                'window_type': window['type']
            })
        
        # Sort events by time
        self.events.sort(key=lambda e: e['time'])
    
    def _compute_base_latency(self) -> float:
        """Compute base propagation latency."""
        if self.mode == 'transparent':
            return 5.0  # ms - one-hop
        else:  # regenerative
            return 10.0  # ms - includes processing delay
    
    def _get_parameters(self) -> Dict:
        """Get simulation parameters."""
        return {
            'relay_mode': self.mode,
            'propagation_model': 'free_space',
            'data_rate_mbps': 50,
            'simulation_duration_sec': 86400,
            'processing_delay_ms': 5.0 if self.mode == 'regenerative' else 0.0,
            'queuing_model': 'fifo',
            'buffer_size_mb': 10
        }
    
    def export_ns3(self, scenario: Dict) -> str:
        """Export as NS-3 Python script."""
        script = f"""#!/usr/bin/env python3
# NS-3 Scenario: {scenario['metadata']['name']}
# Generated: {scenario['metadata']['generated_at']}
# Mode: {scenario['metadata']['mode']}

import ns.core
import ns.network
import ns.point_to_point
import ns.applications

# Create nodes
satellites = ns.network.NodeContainer()
satellites.Create({len(scenario['topology']['satellites'])})

gateways = ns.network.NodeContainer()
gateways.Create({len(scenario['topology']['gateways'])})

# Configure links
p2p = ns.point_to_point.PointToPointHelper()
p2p.SetDeviceAttribute("DataRate", ns.core.StringValue("{scenario['parameters']['data_rate_mbps']}Mbps"))
p2p.SetChannelAttribute("Delay", ns.core.StringValue("{scenario['parameters']['propagation_model']}"))

# Install devices
devices = ns.network.NetDeviceContainer()
for sat_idx in range({len(scenario['topology']['satellites'])}):
    for gw_idx in range({len(scenario['topology']['gateways'])}):
        sat_node = satellites.Get(sat_idx)
        gw_node = gateways.Get(gw_idx)
        device = p2p.Install(sat_node, gw_node)
        devices.Add(device)

# Schedule events
"""
        
        for event in scenario['events']:
            script += f"""
ns.core.Simulator.Schedule(
    ns.core.Time("{event['time']}"),
    lambda: handle_event("{event['type']}", "{event['source']}", "{event['target']}")
)
"""
        
        script += """
# Run simulation
ns.core.Simulator.Stop(ns.core.Seconds({}))
ns.core.Simulator.Run()
ns.core.Simulator.Destroy()
""".format(scenario['parameters']['simulation_duration_sec'])
        
        return script


def main():
    """CLI interface for scenario generation."""
    ap = argparse.ArgumentParser(description="Generate NS-3 scenario from OASIS windows")
    ap.add_argument("windows", type=Path, help="Parsed windows JSON")
    ap.add_argument("-o", "--output", type=Path, default=Path("config/ns3_scenario.json"))
    ap.add_argument("--mode", choices=['transparent', 'regenerative'], default='transparent')
    ap.add_argument("--format", choices=['json', 'ns3'], default='json')
    
    args = ap.parse_args()
    
    # Load windows
    with args.windows.open() as f:
        windows_data = json.load(f)
    
    # Generate scenario
    generator = ScenarioGenerator(mode=args.mode)
    scenario = generator.generate(windows_data)
    
    # Output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    if args.format == 'json':
        args.output.write_text(json.dumps(scenario, indent=2))
    else:  # ns3
        script = generator.export_ns3(scenario)
        args.output.write_text(script)
    
    print(json.dumps({
        'satellites': len(scenario['topology']['satellites']),
        'gateways': len(scenario['topology']['gateways']),
        'links': len(scenario['topology']['links']),
        'events': len(scenario['events']),
        'mode': scenario['metadata']['mode'],
        'output': str(args.output)
    }, indent=2))
    
    return 0


if __name__ == "__main__":
    exit(main())
