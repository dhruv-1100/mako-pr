#!/bin/bash

# Build the project first (ensure this is run in an environment with dependencies)
# make -j4 deptran_server

# Run the server with the deterministic configuration
echo "Starting Deterministic Benchmark..."
./build/deptran_server -f config/deterministic_micro.yml

echo "Benchmark completed."
