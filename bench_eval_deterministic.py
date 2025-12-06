#!/usr/bin/env python3
"""
Benchmark Evaluation Script for Deterministic Mode vs OCC

This script runs TPC-C benchmarks comparing:
1. Deterministic mode (Calvin-style predetermined ordering)
2. OCC mode (Optimistic Concurrency Control)

Under varying contention levels:
- Low contention: 4 warehouses (2 per partition)
- High contention: 2 warehouses (1 per partition)

Results are collected and saved to CSV for analysis.
"""

import os
import subprocess
import time
import re
import csv
from datetime import datetime

# Benchmark duration in seconds
DURATION = 30

# Number of iterations per configuration
ITERATIONS = 3

# Base configuration template
BASE_CONFIG = """
bench:
  workload: tpcc
  scale: 1
  weight:
    new_order: {new_order_weight}
    payment: {payment_weight}
    delivery: 0
    order_status: 0
    stock_level: 0
  population:
    warehouse: {warehouses}
    district: 2
    customer: 3000
    history: 3000
    order: 3000
    new_order: 900
    item: 10000
    stock: {stock}
    order_line: 30000

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
      - {{name: d_id,        type: integer, primary: true}}
      - {{name: d_w_id,      type: integer, primary: true, foreign: warehouse.w_id}}
      - {{name: d_name,      type: string}}
      - {{name: d_street_1,  type: string}}
      - {{name: d_street_2,  type: string}}
      - {{name: d_city,      type: string}}
      - {{name: d_state,     type: string}}
      - {{name: d_zip,       type: string}}
      - {{name: d_tax,       type: double}}
      - {{name: d_ytd,       type: double}}
      - {{name: d_next_o_id, type: integer}}
  - name: customer
    column:
      - {{name: c_id,         type: integer, primary: true}}
      - {{name: c_d_id,       type: integer, primary: true, foreign: district.d_id}}
      - {{name: c_w_id,       type: integer, primary: true, foreign: district.d_w_id}}
      - {{name: c_first,      type: string}}
      - {{name: c_middle,     type: string}}
      - {{name: c_last,       type: string}}
      - {{name: c_street_1,   type: string}}
      - {{name: c_street_2,   type: string}}
      - {{name: c_city,       type: string}}
      - {{name: c_state,      type: string}}
      - {{name: c_zip,        type: string}}
      - {{name: c_phone,      type: string}}
      - {{name: c_since,      type: string}}
      - {{name: c_credit,     type: string}}
      - {{name: c_credit_lim, type: double}}
      - {{name: c_discount,   type: double}}
      - {{name: c_balance,    type: double}}
      - {{name: c_ytd_payment,type: double}}
      - {{name: c_payment_cnt,type: integer}}
      - {{name: c_delivery_cnt,type: integer}}
      - {{name: c_data,       type: string}}
  - name: history
    column:
      - {{name: h_c_id,   type: integer, foreign: customer.c_id}}
      - {{name: h_c_d_id, type: integer, foreign: customer.c_d_id}}
      - {{name: h_c_w_id, type: integer, foreign: customer.c_w_id}}
      - {{name: h_d_id,   type: integer, foreign: district.d_id}}
      - {{name: h_w_id,   type: integer, foreign: district.d_w_id}}
      - {{name: h_date,   type: string}}
      - {{name: h_amount, type: double}}
      - {{name: h_data,   type: string}}
  - name: order
    column:
      - {{name: o_d_id,       type: integer, primary: true, foreign: district.d_id}}
      - {{name: o_w_id,       type: integer, primary: true, foreign: district.d_w_id}}
      - {{name: o_id,         type: integer, primary: true}}
      - {{name: o_c_id,       type: integer, foreign: customer.c_id}}
      - {{name: o_entry_d,    type: string}}
      - {{name: o_carrier_id, type: integer}}
      - {{name: o_ol_cnt,     type: integer}}
      - {{name: o_all_local,  type: integer}}
  - name: new_order
    column:
      - {{name: no_o_id, type: integer, primary: true, foreign: order.o_id}}
      - {{name: no_d_id, type: integer, primary: true, foreign: order.o_d_id}}
      - {{name: no_w_id, type: integer, primary: true, foreign: order.o_w_id}}
  - name: item
    column:
      - {{name: i_id,    type: integer, primary: true}}
      - {{name: i_im_id, type: integer}}
      - {{name: i_name,  type: string}}
      - {{name: i_price, type: double}}
      - {{name: i_data,  type: string}}
  - name: stock
    column:
      - {{name: s_i_id,       type: integer, primary: true, foreign: item.i_id}}
      - {{name: s_w_id,       type: integer, primary: true, foreign: warehouse.w_id}}
      - {{name: s_quantity,   type: integer}}
      - {{name: s_dist_01,    type: string}}
      - {{name: s_dist_02,    type: string}}
      - {{name: s_dist_03,    type: string}}
      - {{name: s_dist_04,    type: string}}
      - {{name: s_dist_05,    type: string}}
      - {{name: s_dist_06,    type: string}}
      - {{name: s_dist_07,    type: string}}
      - {{name: s_dist_08,    type: string}}
      - {{name: s_dist_09,    type: string}}
      - {{name: s_dist_10,    type: string}}
      - {{name: s_ytd,        type: integer}}
      - {{name: s_order_cnt,  type: integer}}
      - {{name: s_remote_cnt, type: integer}}
      - {{name: s_data,       type: string}}
  - name: order_line
    column:
      - {{name: ol_o_id,        type: integer, primary: true, foreign: order.o_id}}
      - {{name: ol_d_id,        type: integer, primary: true, foreign: order.o_d_id}}
      - {{name: ol_w_id,        type: integer, primary: true, foreign: order.o_w_id}}
      - {{name: ol_number,      type: integer, primary: true}}
      - {{name: ol_i_id,        type: integer, foreign: item.i_id}}
      - {{name: ol_supply_w_id, type: integer, foreign: warehouse.w_id}}
      - {{name: ol_delivery_d,  type: string}}
      - {{name: ol_quantity,    type: integer}}
      - {{name: ol_amount,      type: double}}
      - {{name: ol_dist_info,   type: string}}

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

mode:
  cc: {cc_mode}
  ab: {ab_mode}
  read_only: {cc_mode}
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


def generate_config(mode, contention):
    """Generate a YAML config for the given mode and contention level."""
    if mode == "deterministic":
        cc_mode = "deterministic"
        ab_mode = "multi_paxos"
    else:  # OCC
        cc_mode = "occ"
        ab_mode = "none"
    
    if contention == "low":
        warehouses = 4
        new_order_weight = 45
        payment_weight = 43
        stock = 40000  # 10000 * warehouses
    else:  # high
        warehouses = 2
        new_order_weight = 100
        payment_weight = 0
        stock = 40000  # Keep same to avoid stock issues
    
    return BASE_CONFIG.format(
        cc_mode=cc_mode,
        ab_mode=ab_mode,
        warehouses=warehouses,
        new_order_weight=new_order_weight,
        payment_weight=payment_weight,
        stock=stock
    )


def run_benchmark(config_path, duration):
    """Run the benchmark and extract results."""
    cmd = ["./run.py", "-f", config_path, "-d", str(duration), "-P", "18100"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    commits = 0
    throughput = 0
    success = False
    
    while True:
        output = process.stdout.readline()
        if output == b'' and process.poll() is not None:
            break
        if output:
            line = output.decode().strip()
            print(line)
            
            if "BENCHMARK SUCCESS!" in line:
                success = True
            
            # Parse commit counts from summary line
            if "Commit:" in line:
                try:
                    parts = line.split(',')
                    for part in parts:
                        if "Commit:" in part:
                            commits = int(part.split(':')[1].strip())
                except ValueError:
                    pass
            
            # Parse throughput (TPS)
            tps_match = re.search(r'(\d+)\s*tps', line, re.IGNORECASE)
            if tps_match:
                throughput = int(tps_match.group(1))
    
    rc = process.poll()
    
    # Calculate TPS from commits if not directly available
    if throughput == 0 and commits > 0:
        throughput = commits // duration
    
    return {
        "success": success or (rc == 0 and commits > 0),
        "commits": commits,
        "throughput_tps": throughput,
        "exit_code": rc
    }


def main():
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    configs = [
        ("deterministic", "low"),
        ("deterministic", "high"),
        ("occ", "low"),
        ("occ", "high"),
    ]
    
    print("=" * 60)
    print("Deterministic Mode Benchmarking Evaluation")
    print("=" * 60)
    print(f"Duration: {DURATION}s per run")
    print(f"Iterations: {ITERATIONS} per configuration")
    print("=" * 60)
    
    for mode, contention in configs:
        print(f"\n>>> Running {mode.upper()} mode with {contention.upper()} contention <<<")
        
        config_content = generate_config(mode, contention)
        config_path = f"bench_eval_{mode}_{contention}.yml"
        
        with open(config_path, "w") as f:
            f.write(config_content)
        
        for iteration in range(1, ITERATIONS + 1):
            print(f"\n--- Iteration {iteration}/{ITERATIONS} ---")
            
            result = run_benchmark(config_path, DURATION)
            
            results.append({
                "timestamp": timestamp,
                "mode": mode,
                "contention": contention,
                "iteration": iteration,
                "success": result["success"],
                "commits": result["commits"],
                "throughput_tps": result["throughput_tps"],
                "duration_sec": DURATION
            })
            
            print(f"Result: {'SUCCESS' if result['success'] else 'FAILED'}, "
                  f"Commits: {result['commits']}, TPS: {result['throughput_tps']}")
            
            # Small delay between runs
            time.sleep(2)
        
        # Cleanup temp config
        os.remove(config_path)
    
    # Write results to CSV
    output_file = f"benchmark_results_{timestamp}.csv"
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    
    # Calculate averages
    for mode, contention in configs:
        subset = [r for r in results if r["mode"] == mode and r["contention"] == contention]
        avg_tps = sum(r["throughput_tps"] for r in subset) / len(subset)
        avg_commits = sum(r["commits"] for r in subset) / len(subset)
        success_rate = sum(1 for r in subset if r["success"]) / len(subset) * 100
        
        print(f"{mode.upper():15} | {contention.upper():5} | "
              f"Avg TPS: {avg_tps:8.1f} | Avg Commits: {avg_commits:8.1f} | "
              f"Success: {success_rate:.0f}%")
    
    print("=" * 60)
    print(f"Results saved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())
