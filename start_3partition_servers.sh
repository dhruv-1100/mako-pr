#!/bin/bash

# Multi-Partition Deterministic Mode Manual Test
# This script manually starts 3 servers representing 3 partitions
# Then runs a simple client to test cross-partition transactions

echo "=========================================="
echo "Multi-Partition Deterministic Test"
echo "=========================================="
echo ""
echo "Starting 3 servers (3 partitions)..."
echo ""

# Kill any existing servers
pkill -9 deptran_server 2>/dev/null
sleep 1

# Start p0 (Partition 0 - Sequencer)
echo "Starting Partition 0 (Sequencer) on port 8100..."
./build/deptran_server -b -d 15 -f test_det_multipart.yml -P s101 -p 12100 -t 10 &
P0_PID=$!
sleep 2

# Start p1 (Partition 1)
echo "Starting Partition 1 on port 8101..."
./build/deptran_server -b -d 15 -f test_det_multipart.yml -P s201 -p 12101 -t 10 &
P1_PID=$!
sleep 2

# Start p2 (Partition 2)
echo "Starting Partition 2 on port 8102..."
./build/deptran_server -b -d 15 -f test_det_multipart.yml -P s301 -p 12102 -t 10 &
P2_PID=$!
sleep 2

echo ""
echo "All servers started. Processes: $P0_PID, $P1_PID, $P2_PID"
echo "Waiting for servers to initialize..."
sleep 3

# Check if all processes are running
for pid in $P0_PID  $P1_PID $P2_PID; do
    if ! ps -p $pid > /dev/null; then
        echo "ERROR: Server process $pid died!"
        pkill -9 deptran_server
        exit 1
    fi
done

echo "All servers running successfully!"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for any server to exit
wait -n

echo ""
echo "A server exited. Stopping all..."
pkill -9 deptran_server
wait

echo "Test complete."
