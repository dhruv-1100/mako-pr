#!/usr/bin/env python3
"""Quick test of the benchmark script with reduced parameters."""

import os
import sys
sys.path.insert(0, '/home/dp012/Desktop/gitmac/mako-pr')
os.chdir('/home/dp012/Desktop/gitmac/mako-pr')

# Import and modify the benchmark module
import bench_eval_deterministic as bench

# Override parameters for quick test
bench.DURATION = 10
bench.ITERATIONS = 1

# Run with just deterministic high contention
if __name__ == "__main__":
    import subprocess
    import time
    
    print("Quick benchmark test - deterministic mode, high contention")
    
    config_content = bench.generate_config("deterministic", "high")
    config_path = "bench_test_quick.yml"
    
    with open(config_path, "w") as f:
        f.write(config_content)
    
    result = bench.run_benchmark(config_path, 10)
    
    print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"Commits: {result['commits']}")
    print(f"Throughput: {result['throughput_tps']} TPS")
    
    os.remove(config_path)
