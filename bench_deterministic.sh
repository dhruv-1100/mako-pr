#!/bin/bash

# Build the project first (ensure this is run in an environment with dependencies)
# make -j4 deptran_server

# Run the server with the deterministic configuration
echo "Starting Deterministic Benchmark..."
# Launch replicas
./build/dbtest -q config/deterministic_converted.yml -N s2 &
./build/dbtest -q config/deterministic_converted.yml -N s3 &
sleep 2
# Launch leader
./build/dbtest -q config/deterministic_converted.yml -N s1

# Cleanup
pkill -f dbtest

echo "Benchmark completed."
