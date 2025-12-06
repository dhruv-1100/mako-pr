#!/bin/bash
# Benchmark comparison: Mako OCC (2-shard) vs Deterministic (2-partition)
# Uses:
# - dbtest for OCC (Mako's native benchmark)
# - run.py for Deterministic (uses deptran_server)

echo "=============================================="
echo "Mako OCC vs Deterministic Benchmark Comparison"
echo "=============================================="
echo ""

DURATION=30
THREADS=4

# Clean up
pkill -9 dbtest 2>/dev/null
pkill -9 deptran_server 2>/dev/null
sleep 2

echo ">>> OCC 2-Shard (using dbtest) <<<"
echo "Running for $DURATION seconds..."

# Start shard 0
nohup bash bash/shard.sh 2 0 $THREADS localhost > /tmp/occ_shard0.log 2>&1 &
SHARD0_PID=$!
sleep 2

# Start shard 1
nohup bash bash/shard.sh 2 1 $THREADS localhost > /tmp/occ_shard1.log 2>&1 &
SHARD1_PID=$!

sleep $DURATION

# Stop shards
kill $SHARD0_PID $SHARD1_PID 2>/dev/null
wait $SHARD0_PID $SHARD1_PID 2>/dev/null

# Extract OCC results
echo ""
echo "OCC Results:"
OCC_TPS0=$(grep "agg_persist_throughput" /tmp/occ_shard0.log 2>/dev/null | tail -1 | awk '{print $2}' || echo "0")
OCC_TPS1=$(grep "agg_persist_throughput" /tmp/occ_shard1.log 2>/dev/null | tail -1 | awk '{print $2}' || echo "0")
echo "  Shard 0: $OCC_TPS0 ops/sec"
echo "  Shard 1: $OCC_TPS1 ops/sec"

# Calculate OCC total (sum of both shards)
OCC_TOTAL=$(echo "$OCC_TPS0 + $OCC_TPS1" | bc 2>/dev/null || echo "0")
echo "  Total:   $OCC_TOTAL ops/sec"

echo ""
echo ">>> Deterministic 2-Partition (using deptran_server) <<<"
echo "Running for $DURATION seconds..."

# Run deterministic benchmark
DET_OUTPUT=$(./run.py -f test_det_multipart.yml -d $DURATION -P 18100 2>&1)

# Extract deterministic results
DET_COMMITS=$(echo "$DET_OUTPUT" | grep -E "Total:.*Commit:" | tail -1 | awk -F'Commit:' '{print $2}' | awk -F',' '{print $1}' | tr -d ' ')
DET_TPS=$(echo "scale=1; ${DET_COMMITS:-0} / $DURATION" | bc 2>/dev/null || echo "0")

echo ""
echo "Deterministic Results:"
echo "  Commits: ${DET_COMMITS:-0}"
echo "  TPS:     $DET_TPS ops/sec"

echo ""
echo "=============================================="
echo "COMPARISON SUMMARY"
echo "=============================================="
echo ""
echo "| Mode          | TPS (ops/sec) | Notes           |"
echo "|---------------|---------------|-----------------|"
echo "| OCC 2-Shard   | $OCC_TOTAL   | dbtest, 2 shards |"
echo "| Deterministic | $DET_TPS     | 2 partitions     |"
echo ""

# Save results to CSV
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "mode,tps,tool,partitions" > benchmark_comparison_${TIMESTAMP}.csv
echo "occ,$OCC_TOTAL,dbtest,2" >> benchmark_comparison_${TIMESTAMP}.csv
echo "deterministic,$DET_TPS,deptran_server,2" >> benchmark_comparison_${TIMESTAMP}.csv

echo "Results saved to: benchmark_comparison_${TIMESTAMP}.csv"
