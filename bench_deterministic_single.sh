#!/bin/bash

# Run the server with the deterministic configuration (single partition)
echo "Starting Single Partition Deterministic Benchmark..."

# Launch leader (only one node)
./build/dbtest -q config/deterministic_single.yml -N s1

# Cleanup (just in case)
pkill -f dbtest

echo "Benchmark completed."
