#!/usr/bin/env python3
"""
Deterministic Mode Comprehensive Benchmark Suite

Tests across:
- Single partition (1 server)
- Single partition with replicas (1 partition, 3 replicas)
- Multi partition (2 servers, no replicas)
- Multi partition with replicas (2 partitions, 3 replicas each)

TPC-C Workloads:
- new_order only (100% write-heavy)
- mixed (45% new_order, 43% payment)
- payment only (100% read-modify-write)
"""

import os
import subprocess
import time
import csv
from datetime import datetime

os.chdir('/home/dp012/Desktop/gitmac/mako-pr')

DURATION = 20  # seconds per test
ITERATIONS = 2

# TPC-C Schema (shared)
SCHEMA = """
schema:
  - name: warehouse
    column:
      - {name: w_id, type: integer, primary: true}
      - {name: w_name, type: string}
      - {name: w_street_1, type: string}
      - {name: w_street_2, type: string}
      - {name: w_city, type: string}
      - {name: w_state, type: string}
      - {name: w_zip, type: string}
      - {name: w_tax, type: double}
      - {name: w_ytd, type: double}
  - name: district
    column:
      - {name: d_id, type: integer, primary: true}
      - {name: d_w_id, type: integer, primary: true, foreign: warehouse.w_id}
      - {name: d_name, type: string}
      - {name: d_street_1, type: string}
      - {name: d_street_2, type: string}
      - {name: d_city, type: string}
      - {name: d_state, type: string}
      - {name: d_zip, type: string}
      - {name: d_tax, type: double}
      - {name: d_ytd, type: double}
      - {name: d_next_o_id, type: integer}
  - name: customer
    column:
      - {name: c_id, type: integer, primary: true}
      - {name: c_d_id, type: integer, primary: true, foreign: district.d_id}
      - {name: c_w_id, type: integer, primary: true, foreign: district.d_w_id}
      - {name: c_first, type: string}
      - {name: c_middle, type: string}
      - {name: c_last, type: string}
      - {name: c_street_1, type: string}
      - {name: c_street_2, type: string}
      - {name: c_city, type: string}
      - {name: c_state, type: string}
      - {name: c_zip, type: string}
      - {name: c_phone, type: string}
      - {name: c_since, type: string}
      - {name: c_credit, type: string}
      - {name: c_credit_lim, type: double}
      - {name: c_discount, type: double}
      - {name: c_balance, type: double}
      - {name: c_ytd_payment, type: double}
      - {name: c_payment_cnt, type: integer}
      - {name: c_delivery_cnt, type: integer}
      - {name: c_data, type: string}
  - name: history
    column:
      - {name: h_c_id, type: integer, foreign: customer.c_id}
      - {name: h_c_d_id, type: integer, foreign: customer.c_d_id}
      - {name: h_c_w_id, type: integer, foreign: customer.c_w_id}
      - {name: h_d_id, type: integer, foreign: district.d_id}
      - {name: h_w_id, type: integer, foreign: district.d_w_id}
      - {name: h_date, type: string}
      - {name: h_amount, type: double}
      - {name: h_data, type: string}
  - name: order
    column:
      - {name: o_d_id, type: integer, primary: true, foreign: district.d_id}
      - {name: o_w_id, type: integer, primary: true, foreign: district.d_w_id}
      - {name: o_id, type: integer, primary: true}
      - {name: o_c_id, type: integer, foreign: customer.c_id}
      - {name: o_entry_d, type: string}
      - {name: o_carrier_id, type: integer}
      - {name: o_ol_cnt, type: integer}
      - {name: o_all_local, type: integer}
  - name: new_order
    column:
      - {name: no_o_id, type: integer, primary: true, foreign: order.o_id}
      - {name: no_d_id, type: integer, primary: true, foreign: order.o_d_id}
      - {name: no_w_id, type: integer, primary: true, foreign: order.o_w_id}
  - name: item
    column:
      - {name: i_id, type: integer, primary: true}
      - {name: i_im_id, type: integer}
      - {name: i_name, type: string}
      - {name: i_price, type: double}
      - {name: i_data, type: string}
  - name: stock
    column:
      - {name: s_i_id, type: integer, primary: true, foreign: item.i_id}
      - {name: s_w_id, type: integer, primary: true, foreign: warehouse.w_id}
      - {name: s_quantity, type: integer}
      - {name: s_dist_01, type: string}
      - {name: s_dist_02, type: string}
      - {name: s_dist_03, type: string}
      - {name: s_dist_04, type: string}
      - {name: s_dist_05, type: string}
      - {name: s_dist_06, type: string}
      - {name: s_dist_07, type: string}
      - {name: s_dist_08, type: string}
      - {name: s_dist_09, type: string}
      - {name: s_dist_10, type: string}
      - {name: s_ytd, type: integer}
      - {name: s_order_cnt, type: integer}
      - {name: s_remote_cnt, type: integer}
      - {name: s_data, type: string}
  - name: order_line
    column:
      - {name: ol_o_id, type: integer, primary: true, foreign: order.o_id}
      - {name: ol_d_id, type: integer, primary: true, foreign: order.o_d_id}
      - {name: ol_w_id, type: integer, primary: true, foreign: order.o_w_id}
      - {name: ol_number, type: integer, primary: true}
      - {name: ol_i_id, type: integer, foreign: item.i_id}
      - {name: ol_supply_w_id, type: integer, foreign: warehouse.w_id}
      - {name: ol_delivery_d, type: string}
      - {name: ol_quantity, type: integer}
      - {name: ol_amount, type: double}
      - {name: ol_dist_info, type: string}

sharding:
  warehouse: MOD
  district: MOD
  customer: MOD
  history: MOD
  order: MOD
  new_order: MOD
  item: MOD
  stock: MOD
  order_line: MOD
"""

# Workload configurations
WORKLOADS = {
    "new_order": {"new_order": 100, "payment": 0},
    "mixed": {"new_order": 45, "payment": 43},
    "payment": {"new_order": 0, "payment": 100},
}

def create_config(partitions, replicas, workload_name):
    """Generate a deterministic mode config."""
    workload = WORKLOADS[workload_name]
    
    warehouses = partitions  # 1 warehouse per partition
    stock = 10000 * partitions
    
    # Build site config based on partitions and replicas
    if partitions == 1 and replicas == 1:
        # Single partition, no replicas
        site_config = """
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
    elif partitions == 1 and replicas == 3:
        # Single partition with replicas
        site_config = """
site:
  server:
    - ["s1:18101", "s2:18102", "s3:18103"]
  client:
    - ["c1:18100"]

process:
  s1: s1_proc
  s2: s2_proc
  s3: s3_proc
  c1: c1_proc

host:
  localhost: 127.0.0.1
  s1_proc: 127.0.0.1
  s2_proc: 127.0.0.1
  s3_proc: 127.0.0.1
  c1_proc: 127.0.0.1
"""
    elif partitions == 2 and replicas == 1:
        # Multi partition, no replicas
        site_config = """
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
    elif partitions == 2 and replicas == 3:
        # Multi partition with replicas
        site_config = """
site:
  server:
    - ["s1:18101", "s2:18102", "s3:18103"]
    - ["s4:18104", "s5:18105", "s6:18106"]
  client:
    - ["c1:18100"]

process:
  s1: s1_proc
  s2: s2_proc
  s3: s3_proc
  s4: s4_proc
  s5: s5_proc
  s6: s6_proc
  c1: c1_proc

host:
  localhost: 127.0.0.1
  s1_proc: 127.0.0.1
  s2_proc: 127.0.0.1
  s3_proc: 127.0.0.1
  s4_proc: 127.0.0.1
  s5_proc: 127.0.0.1
  s6_proc: 127.0.0.1
  c1_proc: 127.0.0.1
"""
    else:
        raise ValueError(f"Unsupported config: {partitions}p/{replicas}r")
    
    config = f"""
bench:
  workload: tpcc
  scale: 1
  weight:
    new_order: {workload['new_order']}
    payment: {workload['payment']}
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

{site_config}
"""
    return config


def run_benchmark(config_path, duration):
    """Run benchmark and extract commits."""
    cmd = ["./run.py", "-f", config_path, "-d", str(duration), "-P", "18100"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    commits = 0
    success = False
    
    while True:
        output = proc.stdout.readline()
        if output == b'' and proc.poll() is not None:
            break
        if output:
            line = output.decode().strip()
            if "BENCHMARK SUCCESS!" in line:
                success = True
            if "Commit:" in line:
                try:
                    for part in line.split(','):
                        if "Commit:" in part:
                            val = int(part.split(':')[1].strip())
                            if val > commits:
                                commits = val
                except ValueError:
                    pass
    
    proc.poll()
    tps = commits / duration if commits > 0 else 0
    return {"success": success or commits > 0, "commits": commits, "tps": tps}


def main():
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Scenario configurations: (partitions, replicas, description)
    scenarios = [
        (1, 1, "1P-NoRep"),     # Single partition, no replicas
        (1, 3, "1P-3Rep"),      # Single partition, 3 replicas
        (2, 1, "2P-NoRep"),     # Multi partition, no replicas
        (2, 3, "2P-3Rep"),      # Multi partition, 3 replicas
    ]
    
    print("=" * 75)
    print("Deterministic Mode Comprehensive Benchmark")
    print("=" * 75)
    print(f"Duration: {DURATION}s | Iterations: {ITERATIONS}")
    print("=" * 75)
    
    for partitions, replicas, scenario_name in scenarios:
        for workload_name in WORKLOADS.keys():
            test_name = f"{scenario_name}_{workload_name}"
            print(f"\n>>> {test_name} <<<")
            
            config = create_config(partitions, replicas, workload_name)
            config_path = f"bench_det_{test_name}.yml"
            
            with open(config_path, "w") as f:
                f.write(config)
            
            test_results = []
            for i in range(1, ITERATIONS + 1):
                print(f"  Run {i}/{ITERATIONS}...", end=" ", flush=True)
                
                result = run_benchmark(config_path, DURATION)
                test_results.append(result)
                
                results.append({
                    "scenario": scenario_name,
                    "workload": workload_name,
                    "partitions": partitions,
                    "replicas": replicas,
                    "iteration": i,
                    "commits": result["commits"],
                    "tps": round(result["tps"], 2),
                    "success": result["success"]
                })
                
                status = "OK" if result["success"] else "FAIL"
                print(f"{status} | {result['commits']:4d} commits | {result['tps']:.1f} TPS")
                
                time.sleep(2)
            
            # Show average
            avg_tps = sum(r["tps"] for r in test_results) / len(test_results)
            print(f"  Avg: {avg_tps:.1f} TPS")
            
            os.remove(config_path)
    
    # Write CSV
    csv_file = f"deterministic_scenarios_{timestamp}.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    # Summary table
    print("\n" + "=" * 75)
    print("SUMMARY (Average TPS)")
    print("=" * 75)
    print(f"{'Scenario':<15} | {'new_order':>12} | {'mixed':>12} | {'payment':>12}")
    print("-" * 75)
    
    for partitions, replicas, scenario_name in scenarios:
        row = f"{scenario_name:<15}"
        for workload_name in WORKLOADS.keys():
            subset = [r for r in results 
                     if r["scenario"] == scenario_name and r["workload"] == workload_name]
            avg = sum(r["tps"] for r in subset) / len(subset) if subset else 0
            row += f" | {avg:>12.1f}"
        print(row)
    
    print("=" * 75)
    print(f"Results saved to: {csv_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())
