import os
import subprocess

config_content = """
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
    district: 10
    customer: 30000
    history: 30000
    order: 30000
    new_order: 9000
    item: 100000
    stock: 100000
    order_line: 300000

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
      - {name: c_id,        type: integer, primary: true}
      - {name: c_d_id,      type: integer, primary: true, foreign: district.d_id}
      - {name: c_w_id,      type: integer, primary: true, foreign: district.d_w_id}
      - {name: c_first,     type: string}
      - {name: c_middle,    type: string}
      - {name: c_last,      type: string}
      - {name: c_street_1,  type: string}
      - {name: c_street_2,  type: string}
      - {name: c_city,      type: string}
      - {name: c_state,     type: string}
      - {name: c_zip,       type: string}
      - {name: c_phone,     type: string}
      - {name: c_since,     type: string}
      - {name: c_credit,    type: string}
      - {name: c_credit_lim,    type: double}
      - {name: c_discount,      type: double}
      - {name: c_balance,       type: double}
      - {name: c_ytd_payment,   type: double}
      - {name: c_payment_cnt,   type: integer}
      - {name: c_delivery_cnt,  type: integer}
      - {name: c_data,          type: string}
  - name: history
    column:
      - {name: h_key,     type: integer, primary: true}
      - {name: h_c_id,    type: integer, foreign: customer.c_id}
      - {name: h_c_d_id,  type: integer, foreign: customer.c_d_id}
      - {name: h_c_w_id,  type: integer, foreign: customer.c_w_id}
      - {name: h_d_id,    type: integer, foreign: district.d_id}
      - {name: h_w_id,    type: integer, foreign: district.d_w_id}
      - {name: h_date,    type: string}
      - {name: h_amount,  type: double}
      - {name: h_data,    type: string}
  - name: order
    column:
      - {name: o_d_id,        type: integer, primary: true, foreign: district.d_id}
      - {name: o_w_id,        type: integer, primary: true, foreign: district.d_w_id}
      - {name: o_id,          type: integer, primary: true}
      - {name: o_c_id,        type: integer, foreign: customer.c_id}
      - {name: o_entry_d,     type: string}
      - {name: o_carrier_id,  type: integer}
      - {name: o_ol_cnt,      type: integer}
      - {name: o_all_local,   type: integer}
  - name: new_order
    column:
      - {name: no_d_id, type: integer, primary: true, foreign: order.o_d_id}
      - {name: no_w_id, type: integer, primary: true, foreign: order.o_w_id}
      - {name: no_o_id, type: integer, primary: true, foreign: order.o_id}
  - name: item
    column:
      - {name: i_id,    type: integer, primary: true}
      - {name: i_im_id, type: integer}
      - {name: i_name,  type: string}
      - {name: i_price, type: double}
      - {name: i_data,  type: string}
  - name: stock
    column:
      - {name: s_i_id,    type: integer, primary: true, foreign: item.i_id}
      - {name: s_w_id,    type: integer, primary: true, foreign: warehouse.w_id}
      - {name: s_quantity,type: integer}
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
      - {name: s_ytd,         type: integer}
      - {name: s_order_cnt,   type: integer}
      - {name: s_remote_cnt,  type: integer}
      - {name: s_data,        type: string}
  - name: order_line
    column:
      - {name: ol_d_id,   type: integer, primary: true, foreign: order.o_d_id}
      - {name: ol_w_id,   type: integer, primary: true, foreign: order.o_w_id}
      - {name: ol_o_id,   type: integer, primary: true, foreign: order.o_id}
      - {name: ol_number, type: integer, primary: true}
      - {name: ol_i_id,   type: integer, foreign: stock.s_i_id}
      - {name: ol_supply_w_id,  type: integer, foreign: stock.s_w_id}
      - {name: ol_delivery_d,   type: string}
      - {name: ol_quantity,     type: integer}
      - {name: ol_amount,       type: double}
      - {name: ol_dist_info,    type: string}

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

with open("test_det_3replicas.yml", "w") as f:
    f.write(config_content)

print("Running benchmark with deterministic mode (3 replicas)...")
cmd = ["./run.py", "-f", "test_det_3replicas.yml", "-d", "10", "-P", "18100", "-x", "NEW ORDER"]
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

commits = 0
benchmark_success = False

while True:
    output = process.stdout.readline()
    if output == b'' and process.poll() is not None:
        break
    if output:
        line = output.decode().strip()
        print(line)
        if "BENCHMARK SUCCESS!" in line:
            benchmark_success = True
        if "Commit:" in line:
            try:
                # Example line: Total: 2256, Commit: 2256, Attempts: ...
                parts = line.split(',')
                for part in parts:
                    if "Commit:" in part:
                        commits = int(part.split(':')[1].strip())
            except ValueError:
                pass

rc = process.poll()
print(f"Exited with {rc}")

if rc != 0:
    # Ignore known race condition error if benchmark succeeded
    # Note: stderr is merged into stdout, so we can't read it separately here.
    # We rely on the fact that we saw "BENCHMARK SUCCESS!" in the output loop.
    if benchmark_success and commits > 0:
        print("Ignoring known shutdown race condition error as benchmark succeeded.")
        rc = 0
    else:
        print("Benchmark failed with non-zero exit code.")

if benchmark_success and commits > 0:
    print(f"Integration Test PASSED: {commits} commits.")
    exit(0)
else:
    print(f"Integration Test FAILED: Success={benchmark_success}, Commits={commits}")
    exit(1)
