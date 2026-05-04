#!/usr/bin/env python3
"""
Simple Force Run - Phase 3.2
=============================

Directly calls market_dynamic API endpoint multiple times.
"""

import requests
import time
import sys

def force_run(iterations: int = 20):
    """Call market_dynamic run API N times"""
    
    base_url = "http://localhost:8001"
    
    print(f"\n{'='*60}")
    print(f"🚀 FORCE RUN: market_dynamic x{iterations} iterations")
    print(f"{'='*60}\n")
    
    # Check if there's a manual run endpoint
    endpoints_to_try = [
        "/api/experiments/market_dynamic/run",
        "/api/market-dynamic/run",
        "/api/trading/run",
    ]
    
    success_count = 0
    
    for i in range(iterations):
        print(f"[{i+1}/{iterations}] Attempting run...")
        
        # Try different endpoints
        for endpoint in endpoints_to_try:
            try:
                resp = requests.post(f"{base_url}{endpoint}", timeout=10)
                if resp.status_code == 200:
                    print(f"  └─ ✅ Success via {endpoint}")
                    success_count += 1
                    break
            except Exception as e:
                continue
        else:
            print(f"  └─ ⚠️  No working endpoint found")
        
        time.sleep(0.5)  # Small delay
    
    print(f"\n{'='*60}")
    print(f"📊 Completed: {success_count}/{iterations} successful runs")
    print(f"{'='*60}\n")
    
    if success_count > 0:
        print("Next step:")
        print("  curl http://localhost:8001/api/debug/features-from-shadow\n")
    else:
        print("⚠️  No successful runs - need to find the correct API endpoint\n")

if __name__ == "__main__":
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    force_run(iterations)
