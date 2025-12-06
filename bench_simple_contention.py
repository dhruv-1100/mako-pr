#!/usr/bin/env python3
"""
Simple benchmark comparing deterministic mode under different contention levels.
"""

import os
import subprocess
import time
import csv
from datetime import datetime

os.chdir('/home/dp012/Desktop/gitmac/mako-pr')

# Use existing test_det_multipart.py config as base (known working)
CONFIG_TEMPLATE = """
bench:
  workload: tpcc
  scale: 1
  weight:
    new_order: {new_order}
    payment: {payment}
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
    stock: 40000
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
                            commits = int(part.split(':')[1].strip())
                except:
                    pass
    
    proc.poll()
    return success or commits > 0, commits

def main():
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    duration = 15  # seconds per run
    
    # Test configs: (name, warehouses, new_order%, payment%)
    configs = [
        ("high_contention", 2, 100, 0),   # 2 warehouses, 100% new_order
        ("low_contention", 4, 45, 43),    # 4 warehouses, mixed workload
    ]
    
    print("=" * 60)
    print("Deterministic Mode Contention Benchmark")
    print("=" * 60)
    
    for name, warehouses, new_order, payment in configs:
        print(f"\n>>> Running {name} <<<")
        
        config = CONFIG_TEMPLATE.format(
            warehouses=warehouses,
            new_order=new_order,
            payment=payment
        )
        
        config_path = f"bench_simple_{name}.yml"
        with open(config_path, "w") as f:
            f.write(config)
        
        for i in range(2):  # 2 iterations
            print(f"  Iteration {i+1}/2...")
            success, commits = run_benchmark(config_path, duration)
            tps = commits // duration if commits > 0 else 0
            
            results.append({
                "config": name,
                "iteration": i + 1,
                "success": success,
                "commits": commits,
                "tps": tps,
                "duration": duration
            })
            print(f"    Result: {'OK' if success else 'FAIL'}, Commits: {commits}, TPS: {tps}")
            time.sleep(2)
        
        os.remove(config_path)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, _, _, _ in configs:
        subset = [r for r in results if r["config"] == name]
        avg_tps = sum(r["tps"] for r in subset) / len(subset)
        avg_commits = sum(r["commits"] for r in subset) / len(subset)
        print(f"{name:20} | Avg TPS: {avg_tps:6.1f} | Avg Commits: {avg_commits:6.1f}")
    
    # Save to CSV
    csv_file = f"deterministic_benchmark_{timestamp}.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\nResults saved to: {csv_file}")
    return 0

if __name__ == "__main__":
    exit(main())
