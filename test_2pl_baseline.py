#!/usr/bin/env python3
"""
Quick 2PL baseline test to verify configuration works
"""

import subprocess
import sys

print("Testing 2PL baseline configuration...")
print("Running 10-second benchmark...\n")

cmd = ['./run.py', '-f', 'test_baseline_2pl.yml', '-d', '10', '-P', '12000', '-x', 'NEW ORDER']
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

commits = 0
benchmark_success = False

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
                    if "Commit:" in part:
                        commits = int(part.split(':')[1].strip())
            except ValueError:
                pass

rc = process.poll()

print(f"\n{'='*60}")
print(f"2PL Baseline Test Results:")
print(f"  Commits: {commits}")
print(f"  Success: {benchmark_success}")
print(f"  Exit Code: {rc}")
print(f"{'='*60}\n")

if commits > 0 and benchmark_success:
    print("✅ 2PL baseline configuration is working!")
    sys.exit(0)
else:
    print("❌ 2PL baseline test failed")
    sys.exit(1)
