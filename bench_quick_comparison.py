#!/usr/bin/env python3
"""Quick benchmark comparison test with reduced parameters."""
import os
os.chdir('/home/dp012/Desktop/gitmac/mako-pr')

import bench_extended as b

# Override for quick test
b.DURATION = 15
b.ITERATIONS = 1

if __name__ == "__main__":
    exit(b.main())
