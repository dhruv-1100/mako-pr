#!/usr/bin/env python3
"""
Benchmark Evaluation - Reduced parameters for faster iteration.
Duration: 15s, Iterations: 2
"""

import os
import sys
os.chdir('/home/dp012/Desktop/gitmac/mako-pr')

import bench_eval_deterministic as bench

# Reduce parameters for faster evaluation
bench.DURATION = 15
bench.ITERATIONS = 2

if __name__ == "__main__":
    exit(bench.main())
