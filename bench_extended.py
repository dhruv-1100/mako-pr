#!/usr/bin/env python3
"""
Extended Benchmark Evaluation for Mako Deterministic Mode

Features:
1. Compares deterministic mode vs OCC (single-partition for fair comparison)
2. Longer duration (60s) with 5 iterations
3. Tracks latency via captured timestamps in output
4. Produces CSV with throughput and latency percentiles
"""

import os
import subprocess
import time
import re
import csv
import statistics
from datetime import datetime

os.chdir('/home/dp012/Desktop/gitmac/mako-pr')

# Benchmark parameters
DURATION = 60  # seconds per run
ITERATIONS = 5
WARMUP_DURATION = 10  # seconds to exclude from results

# TPC-C schema (shared across all configs)
SCHEMA = """
schema:
  - name: warehouse
    column:
      - name: w_id
        type: integer
        primary: true
      - name: w_name
        type: string
      - name: w_street_1
        type: string
      - name: w_street_2
        type: string
      - name: w_city
        type: string
      - name: w_state
        type: string
      - name: w_zip
        type: string
      - name: w_tax
        type: double
      - name: w_ytd
        type: double
  - name: district
    column:
      - {name: d_id,        type: integer, primary: true}
      - {name: d_w_id,      type: integer, primary: true, foreign: warehouse.w_id}
      - {name: d_name,      type: string}
      - {name: d_street_1,  type: string}
      - {name: d_street_2,  type: string}
      - {name: d_city,      type: string}
      - {name: d_state,     type: string}
      - {name: d_zip,       type: string}
      - {name: d_tax,       type: double}
      - {name: d_ytd,       type: double}
      - {name: d_next_o_id, type: integer}
  - name: customer
    column:
      - {name: c_id,         type: integer, primary: true}
      - {name: c_d_id,       type: integer, primary: true, foreign: district.d_id}
      - {name: c_w_id,       type: integer, primary: true, foreign: district.d_w_id}
      - {name: c_first,      type: string}
      - {name: c_middle,     type: string}
      - {name: c_last,       type: string}
      - {name: c_street_1,   type: string}
      - {name: c_street_2,   type: string}
      - {name: c_city,       type: string}
      - {name: c_state,      type: string}
      - {name: c_zip,        type: string}
      - {name: c_phone,      type: string}
      - {name: c_since,      type: string}
      - {name: c_credit,     type: string}
      - {name: c_credit_lim, type: double}
      - {name: c_discount,   type: double}
      - {name: c_balance,    type: double}
      - {name: c_ytd_payment,type: double}
      - {name: c_payment_cnt,type: integer}
      - {name: c_delivery_cnt,type: integer}
      - {name: c_data,       type: string}
  - name: history
    column:
      - {name: h_c_id,   type: integer, foreign: customer.c_id}
      - {name: h_c_d_id, type: integer, foreign: customer.c_d_id}
      - {name: h_c_w_id, type: integer, foreign: customer.c_w_id}
      - {name: h_d_id,   type: integer, foreign: district.d_id}
      - {name: h_w_id,   type: integer, foreign: district.d_w_id}
      - {name: h_date,   type: string}
      - {name: h_amount, type: double}
      - {name: h_data,   type: string}
  - name: order
    column:
      - {name: o_d_id,       type: integer, primary: true, foreign: district.d_id}
      - {name: o_w_id,       type: integer, primary: true, foreign: district.d_w_id}
      - {name: o_id,         type: integer, primary: true}
      - {name: o_c_id,       type: integer, foreign: customer.c_id}
      - {name: o_entry_d,    type: string}
      - {name: o_carrier_id, type: integer}
      - {name: o_ol_cnt,     type: integer}
      - {name: o_all_local,  type: integer}
  - name: new_order
    column:
      - {name: no_o_id, type: integer, primary: true, foreign: order.o_id}
      - {name: no_d_id, type: integer, primary: true, foreign: order.o_d_id}
      - {name: no_w_id, type: integer, primary: true, foreign: order.o_w_id}
  - name: item
    column:
      - {name: i_id,    type: integer, primary: true}
      - {name: i_im_id, type: integer}
      - {name: i_name,  type: string}
      - {name: i_price, type: double}
      - {name: i_data,  type: string}
  - name: stock
    column:
      - {name: s_i_id,       type: integer, primary: true, foreign: item.i_id}
      - {name: s_w_id,       type: integer, primary: true, foreign: warehouse.w_id}
      - {name: s_quantity,   type: integer}
      - {name: s_dist_01,    type: string}
      - {name: s_dist_02,    type: string}
      - {name: s_dist_03,    type: string}
      - {name: s_dist_04,    type: string}
      - {name: s_dist_05,    type: string}
      - {name: s_dist_06,    type: string}
      - {name: s_dist_07,    type: string}
      - {name: s_dist_08,    type: string}
      - {name: s_dist_09,    type: string}
      - {name: s_dist_10,    type: string}
      - {name: s_ytd,        type: integer}
      - {name: s_order_cnt,  type: integer}
      - {name: s_remote_cnt, type: integer}
      - {name: s_data,       type: string}
  - name: order_line
    column:
      - {name: ol_o_id,        type: integer, primary: true, foreign: order.o_id}
      - {name: ol_d_id,        type: integer, primary: true, foreign: order.o_d_id}
      - {name: ol_w_id,        type: integer, primary: true, foreign: order.o_w_id}
      - {name: ol_number,      type: integer, primary: true}
      - {name: ol_i_id,        type: integer, foreign: item.i_id}
      - {name: ol_supply_w_id, type: integer, foreign: warehouse.w_id}
      - {name: ol_delivery_d,  type: string}
      - {name: ol_quantity,    type: integer}
      - {name: ol_amount,      type: double}
      - {name: ol_dist_info,   type: string}

sharding:
  warehouse:  MOD
  district:   MOD
  customer:   MOD
  history:    MOD
  order:      MOD
  new_order:  MOD
  item:       MOD
  stock:      MOD
  order_line: MOD
"""

def create_deterministic_config_2p():
    """Deterministic mode with 2 partitions for multi-partition txns."""
    return f"""
bench:
  workload: tpcc
  scale: 1
  weight:
    new_order: 100
    payment: 0
    delivery: 0
    order_status: 0
    stock_level: 0
  population:
    warehouse: 2
    district: 2
    customer: 3000
    history: 3000
    order: 3000
    new_order: 900
    item: 10000
    stock: 40000
    order_line: 30000

{SCHEMA}

mode:
  cc: deterministic
  ab: multi_paxos
  read_only: deterministic
  batch: false
  retry: 20
  ongoing: 1

client:
  type: closed
  rate: 100

site:
  server:
    - ["s1:18101"]
    - ["s2:18102"]
  client:
    - ["c1:18100"]

process:
  s1: s1_proc
  s2: s2_proc
  c1: c1_proc

host:
  localhost: 127.0.0.1
  s1_proc: 127.0.0.1
  s2_proc: 127.0.0.1
  c1_proc: 127.0.0.1
"""


def create_occ_config_1p():
    """OCC mode with 1 partition (single-node for fair comparison)."""
    return f"""
bench:
  workload: tpcc
  scale: 1
  weight:
    new_order: 100
    payment: 0
    delivery: 0
    order_status: 0
    stock_level: 0
  population:
    warehouse: 1
    district: 2
    customer: 3000
    history: 3000
    order: 3000
    new_order: 900
    item: 10000
    stock: 10000
    order_line: 30000

{SCHEMA}

mode:
  cc: occ
  ab: none
  read_only: occ
  batch: false
  retry: 20
  ongoing: 1

client:
  type: closed
  rate: 100

site:
  server:
    - ["s1:18101"]
  client:
    - ["c1:18100"]

process:
  s1: s1_proc
  c1: c1_proc

host:
  localhost: 127.0.0.1
  s1_proc: 127.0.0.1
  c1_proc: 127.0.0.1
"""


def create_deterministic_config_1p():
    """Deterministic mode with 1 partition (for fair OCC comparison)."""
    return f"""
bench:
  workload: tpcc
  scale: 1
  weight:
    new_order: 100
    payment: 0
    delivery: 0
    order_status: 0
    stock_level: 0
  population:
    warehouse: 1
    district: 2
    customer: 3000
    history: 3000
    order: 3000
    new_order: 900
    item: 10000
    stock: 10000
    order_line: 30000

{SCHEMA}

mode:
  cc: deterministic
  ab: multi_paxos
  read_only: deterministic
  batch: false
  retry: 20
  ongoing: 1

client:
  type: closed
  rate: 100

site:
  server:
    - ["s1:18101"]
  client:
    - ["c1:18100"]

process:
  s1: s1_proc
  c1: c1_proc

host:
  localhost: 127.0.0.1
  s1_proc: 127.0.0.1
  c1_proc: 127.0.0.1
"""


def run_benchmark(config_path, duration):
    """Run benchmark and extract commits + latency from output."""
    cmd = ["./run.py", "-f", config_path, "-d", str(duration), "-P", "18100"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    commits = 0
    success = False
    latencies = []
    
    while True:
        output = proc.stdout.readline()
        if output == b'' and proc.poll() is not None:
            break
        if output:
            line = output.decode().strip()
            
            if "BENCHMARK SUCCESS!" in line:
                success = True
            
            # Parse commit counts - keep the last (largest) value
            if "Commit:" in line:
                try:
                    for part in line.split(','):
                        if "Commit:" in part:
                            val = int(part.split(':')[1].strip())
                            if val > commits:  # Keep largest value
                                commits = val
                except ValueError:
                    pass
            
            # Parse latencies from output (if instrumented)
            # Format: "latency_us: 12345"
            lat_match = re.search(r'latency_us:\s*(\d+)', line)
            if lat_match:
                latencies.append(int(lat_match.group(1)))
    
    proc.poll()
    
    # Calculate latency stats
    lat_stats = {}
    if latencies:
        latencies.sort()
        lat_stats['median'] = statistics.median(latencies)
        lat_stats['p99'] = latencies[int(len(latencies) * 0.99)]
        lat_stats['mean'] = statistics.mean(latencies)
    else:
        lat_stats['median'] = 0
        lat_stats['p99'] = 0
        lat_stats['mean'] = 0
    
    tps = commits // duration if commits > 0 else 0
    
    return {
        "success": success or commits > 0,
        "commits": commits,
        "tps": tps,
        "latency_median_us": lat_stats['median'],
        "latency_p99_us": lat_stats['p99'],
        "latency_mean_us": lat_stats['mean']
    }


def main():
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Configurations to test
    configs = [
        ("deterministic_2p", "Deterministic (2 partitions)", create_deterministic_config_2p),
        ("deterministic_1p", "Deterministic (1 partition)", create_deterministic_config_1p),
        ("occ_1p", "OCC (1 partition)", create_occ_config_1p),
    ]
    
    print("=" * 70)
    print("Extended Benchmark Evaluation: Deterministic vs OCC")
    print("=" * 70)
    print(f"Duration: {DURATION}s per run")
    print(f"Iterations: {ITERATIONS}")
    print("=" * 70)
    
    for config_id, config_name, config_gen in configs:
        print(f"\n>>> {config_name} <<<")
        
        config_content = config_gen()
        config_path = f"bench_extended_{config_id}.yml"
        
        with open(config_path, "w") as f:
            f.write(config_content)
        
        for i in range(1, ITERATIONS + 1):
            print(f"  Iteration {i}/{ITERATIONS}...", end=" ", flush=True)
            
            result = run_benchmark(config_path, DURATION)
            
            results.append({
                "config": config_id,
                "config_name": config_name,
                "iteration": i,
                "success": result["success"],
                "commits": result["commits"],
                "tps": result["tps"],
                "latency_median_us": result["latency_median_us"],
                "latency_p99_us": result["latency_p99_us"],
                "duration": DURATION
            })
            
            status = "OK" if result["success"] else "FAIL"
            print(f"{status} | {result['commits']:6d} commits | {result['tps']:4d} tps")
            
            time.sleep(3)  # Cooldown between runs
        
        os.remove(config_path)
    
    # Write results to CSV
    csv_file = f"extended_benchmark_{timestamp}.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY (Averages across iterations)")
    print("=" * 70)
    print(f"{'Config':<30} | {'Commits':>10} | {'TPS':>8} | {'Lat(median)':>12}")
    print("-" * 70)
    
    for config_id, config_name, _ in configs:
        subset = [r for r in results if r["config"] == config_id]
        if not subset:
            continue
        avg_commits = sum(r["commits"] for r in subset) / len(subset)
        avg_tps = sum(r["tps"] for r in subset) / len(subset)
        avg_lat = sum(r["latency_median_us"] for r in subset) / len(subset)
        print(f"{config_name:<30} | {avg_commits:>10.0f} | {avg_tps:>8.1f} | {avg_lat:>10.0f} us")
    
    print("=" * 70)
    print(f"Results saved to: {csv_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())
