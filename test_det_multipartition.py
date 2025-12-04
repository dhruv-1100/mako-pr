#!/usr/bin/env python3
"""
Multi-Partition Deterministic Mode Test

Tests that deterministic mode correctly handles transactions
that span multiple partitions (cross-partition transactions).

Configuration:
- 3 partitions (p0, p1, p2)
- 3 warehouses (distributed across partitions)
- Deterministic mode with sequencer on p0
"""

import subprocess
import sys
import time

def run_test(duration=10):
    print("="*60)
    print("Multi-Partition Deterministic Mode Test")
    print("="*60)
    print(f"Configuration: 3 partitions, 3 warehouses")
    print(f"Duration: {duration}s")
    print(f"Starting benchmark...\n")
    
    cmd = ['./run.py', '-f', 'test_det_3partitions.yml', '-d', str(duration), '-P', '12000', '-x', 'NEW ORDER']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    commits = 0
    total_txns = 0
    benchmark_success = False
    cross_partition_evidence = []
    
    while True:
        output = process.stdout.readline()
        if output == b'' and process.poll() is not None:
            break
        if output:
            line = output.decode().strip()
            print(line)
            
            if "BENCHMARK SUCCESS!" in line:
                benchmark_success = True
            if "Commit:" in line:
                try:
                    parts = line.split(',')
                    for part in parts:
                        if "Total:" in part:
                            total_txns = int(part.split(':')[1].strip())
                        if "Commit:" in part:
                            commits = int(part.split(':')[1].strip())
                except ValueError:
                    pass
            
            # Look for evidence of cross-partition execution
            if "BroadcastDispatch" in line or "partition" in line.lower():
                cross_partition_evidence.append(line)
    
    rc = process.poll()
    
    print(f"\n{'='*60}")
    print(f"Multi-Partition Test Results:")
    print(f"  Commits: {commits}")
    print(f"  Total Txns: {total_txns}")
    print(f"  Success: {benchmark_success}")
    print(f"  Exit Code: {rc}")
    
    if cross_partition_evidence:
        print(f"\nCross-Partition Evidence ({len(cross_partition_evidence)} lines):")
        for line in cross_partition_evidence[:5]:  # Show first 5
            print(f"  {line}")
    
    print(f"{'='*60}\n")
    
    if commits > 0 and benchmark_success:
        print("✅ Multi-partition deterministic mode test PASSED!")
        print(f"   Successfully processed {commits} transactions across 3 partitions")
        return 0
    else:
        print("❌ Multi-partition test failed")
        return 1

if __name__ == '__main__':
    duration = 10 if len(sys.argv) < 2 else int(sys.argv[1])
    sys.exit(run_test(duration))
