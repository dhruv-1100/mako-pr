#!/usr/bin/env python3
"""
Simple Multi-Partition Test - Direct Verification

Tests multi-partition transaction handling by:
1. Starting a single-node server with 1 partition (Baseline)
2. Starting 3 servers for 3 partitions (Multi-Partition)
3. Running a client to verify cross-partition transactions

This bypasses run.py complexity.
"""

import subprocess
import sys
import time
import os
import signal

def cleanup_processes():
    subprocess.run(['pkill', '-9', 'deptran_server'], stderr=subprocess.DEVNULL)
    time.sleep(1)

def test_single_partition_baseline():
    """Test that single partition deterministic mode works as baseline"""
    print("="*60)
    print("Step 1: Single-Partition Baseline Test")
    print("="*60)
    
    cleanup_processes()
    
    # Start single server
    print("Starting single-partition server...")
    server_proc = subprocess.Popen([
        './build/deptran_server',
        '-b', '-d', '10',
        '-f', 'test_det.yml',
        '-P', 's1',
        '-p', '8101',
        '-t', '10'
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
    
    time.sleep(3)
    
    # Check if server is running
    if server_proc.poll() is not None:
        print("ERROR: Server failed to start")
        output, _ = server_proc.communicate()
        print(output.decode())
        return False
    
    print("✅ Server started successfully")
    
    # Run a quick client test using test_det.py logic (but simplified)
    print("\nRunning benchmark client...")
    # We can use run.py just for the client if we want, OR we can run deptran_server as client
    # Let's use run.py for client as it's easier to parse output, but we need to be careful about what it starts.
    # Actually, let's use test_det.py which wraps run.py but we want to avoid run.py starting servers.
    # run.py has a 'client only' mode? No, but we can use deptran_server as client directly.
    
    # Command for client:
    # ./build/deptran_server -f test_det.yml -P c1 -d 10 -b -t 10 -r -p 12000
    client_cmd = [
        './build/deptran_server',
        '-f', 'test_det.yml',
        '-P', 'c1',
        '-d', '5',
        '-b',
        '-p', '8500',
        '-t', '10'
    ]
    
    client_proc = subprocess.Popen(client_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    
    commits = 0
    success = False
    
    try:
        output, _ = client_proc.communicate(timeout=30)
        # print(output) # Optional
        
        if "BENCHMARK SUCCESS" in output:
            success = True
            
        for line in output.split('\n'):
            if "Commit:" in line:
                print(f"  {line}")
                try:
                    parts = line.split(',')
                    for part in parts:
                        if "Commit:" in part:
                            commits = int(part.split(':')[1].strip())
                except:
                    pass
    except subprocess.TimeoutExpired:
        client_proc.kill()
        output, _ = client_proc.communicate()
        print("❌ Client timed out")
        print("--- Client Output ---")
        print(output)
        print("---------------------")
        return False

    cleanup_processes()
    
    if commits > 0:
        print(f"✅ Single-partition test PASSED (Commits: {commits})")
        return True
    else:
        print("❌ Single-partition test FAILED (0 commits)")
        return False

def test_multi_partition_execution():
    """Test actual multi-partition execution by starting 3 servers"""
    print("\n" + "="*60)
    print("Step 2: Multi-Partition Execution Test")
    print("="*60)
    
    cleanup_processes()
    
    # Start 3 servers
    servers = []
    # Ports must match test_det_multipart.yml:
    # s101: 8100
    # s201: 8101
    # s301: 8102
    configs = [
        ('s101', '8100'), # Partition 0
        ('s201', '8101'), # Partition 1
        ('s301', '8102')  # Partition 2
    ]
    
    print("Starting 3 servers...")
    for proc_name, port in configs:
        print(f"  Starting {proc_name} on port {port}...")
        proc = subprocess.Popen([
            './build/deptran_server',
            '-b', '-d', '15',
            '-f', 'test_det_multipart.yml',
            '-P', proc_name,
            '-p', port,
            '-t', '10'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
        servers.append(proc)
        time.sleep(1) # Wait a bit between starts
        
        if proc.poll() is not None:
            print(f"❌ Server {proc_name} failed to start immediately")
            print(proc.stdout.read())
            cleanup_processes()
            return False

    print("✅ All servers started. Waiting for initialization...")
    time.sleep(5)
    
    # Check if they are still running
    for i, proc in enumerate(servers):
        if proc.poll() is not None:
            print(f"❌ Server {configs[i][0]} died during initialization")
            print(proc.stdout.read())
            cleanup_processes()
            return False
            
    print("✅ Servers running. Starting Client...")
    
    # Start Client
    client_cmd = [
        './build/deptran_server',
        '-f', 'test_det_multipart.yml',
        '-P', 'c101',
        '-d', '5',
        '-b',
        '-p', '8501',
        '-t', '10'
    ]
    
    client_proc = subprocess.Popen(client_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    
    try:
        output, _ = client_proc.communicate(timeout=30)
        print(output)
        
        if "BENCHMARK SUCCESS" in output:
            success = True
        
        for line in output.split('\n'):
            if "Commit:" in line:
                print(f"  {line}")
                try:
                    parts = line.split(',')
                    for part in parts:
                        if "Commit:" in part:
                            commits = int(part.split(':')[1].strip())
                except:
                    pass
    except subprocess.TimeoutExpired:
        client_proc.kill()
        output, _ = client_proc.communicate()
        print("❌ Client timed out")
        print("--- Client Output ---")
        print(output)
        print("---------------------")
        return False
    
    # Cleanup
    cleanup_processes()
    
    if commits > 0:
        print(f"✅ Multi-partition test PASSED (Commits: {commits})")
        return True
    else:
        print("❌ Multi-partition test FAILED (0 commits)")
        return False

def main():
    print("\n" + "="*60)
    print("SIMPLE MULTI-PARTITION INTEGRATION TEST")
    print("="*60)
    
    # Step 1: Verify single-partition works
    if not test_single_partition_baseline():
        return 1
    
    # Step 2: Verify multi-partition execution
    if not test_multi_partition_execution():
        return 1
    
    print("\n" + "="*60)
    print("✅ TEST SUMMARY")
    print("="*60)
    print("✅ Single-partition deterministic mode: WORKING")
    print("✅ Multi-partition deterministic mode: WORKING")
    print("="*60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
