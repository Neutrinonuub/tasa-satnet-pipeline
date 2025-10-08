#!/usr/bin/env python3
"""Health check script for container."""
import sys
import os

def check_health():
    """Check if application is healthy."""
    try:
        # Check if critical scripts exist
        scripts = [
            "scripts/parse_oasis_log.py",
            "scripts/gen_scenario.py",
            "scripts/metrics.py",
            "scripts/scheduler.py"
        ]
        
        for script in scripts:
            if not os.path.exists(script):
                print(f"FAIL: Missing {script}")
                return 1
        
        # Check if Python imports work
        try:
            import json
            import argparse
            from datetime import datetime
        except ImportError as e:
            print(f"FAIL: Import error: {e}")
            return 1
        
        print("OK: Health check passed")
        return 0
        
    except Exception as e:
        print(f"FAIL: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_health())
