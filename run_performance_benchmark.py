#!/usr/bin/env python3
"""
Performance Benchmark Runner for Deterministic Mode Evaluation
Compares deterministic mode against baseline 2PL on TPCC workload
"""

import subprocess
import json
import time
import os
from datetime import datetime

class BenchmarkRunner:
    def __init__(self):
        self.results = {}
        
    def run_benchmark(self, config_file, duration=60, label=""):
        """Run a single benchmark configuration"""
        print(f"\n{'='*60}")
        print(f"Running benchmark: {label}")
        print(f"Config: {config_file}")
        print(f"Duration: {duration}s")
        print(f"{'='*60}\n")
        
        cmd = ['./run.py', '-f', config_file, '-d', str(duration), '-P', '12000', '-x', 'NEW ORDER']
        
        start_time = time.time()
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        commits = 0
        total_txns = 0
        benchmark_success = False
        output_lines = []
        
        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                line = output.decode().strip()
                output_lines.append(line)
                if "BENCHMARK SUCCESS!" in line:
                    benchmark_success = True
                if "Commit:" in line:
                    try:
                        parts = line.split(',')
                        for part in parts:
                            if "Total:" in part:
                                total_txns = int(part.split(':')[1].strip())
                            if "Commit:" in part:
                                commits = int(part.split(':')[1].strip())
                    except ValueError:
                        pass
        
        end_time = time.time()
        actual_duration = end_time - start_time
        tps = commits / duration if duration > 0 else 0
        
        result = {
            'config': config_file,
            'label': label,
            'commits': commits,
            'total_txns': total_txns,
            'duration': duration,
            'actual_duration': actual_duration,
            'tps': tps,
            'success': benchmark_success,
            'timestamp': datetime.now().isoformat()
        }
        
        self.results[label] = result
        
        print(f"\n{'-'*60}")
        print(f"Results for {label}:")
        print(f"  Commits: {commits}")
        print(f"  Total Txns: {total_txns}")
        print(f"  TPS: {tps:.2f}")
        print(f"  Success: {benchmark_success}")
        print(f"{'-'*60}\n")
        
        return result
    
    def save_results(self, filename="benchmark_results.json"):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to {filename}")
    
    def print_summary(self):
        """Print comparison summary"""
        print(f"\n{'='*60}")
        print("BENCHMARK COMPARISON SUMMARY")
        print(f"{'='*60}\n")
        
        print(f"{'Configuration':<30} {'TPS':<15} {'Commits':<10}")
        print(f"{'-'*60}")
        
        baseline_tps = None
        for label, result in self.results.items():
            tps = result['tps']
            commits = result['commits']
            
            if 'baseline' in label.lower() or '2pl' in label.lower():
                baseline_tps = tps
                overhead = ""
            elif baseline_tps:
                overhead = f"({(tps/baseline_tps - 1)*100:+.1f}%)"
            else:
                overhead = ""
            
            print(f"{label:<30} {tps:>8.2f} TPS  {commits:>8}  {overhead}")
        
        print(f"{'-'*60}\n")

def main():
    runner = BenchmarkRunner()
    
    # Test duration (use 60 for full benchmark, 10 for quick test)
    DURATION = 60
    
    print(f"\nStarting Performance Evaluation")
    print(f"Duration per benchmark: {DURATION}s")
    print(f"Total estimated time: ~{DURATION * 3 / 60:.1f} minutes\n")
    
    # Run benchmarks
    try:
        # 1. Baseline 2PL
        runner.run_benchmark(
            'test_baseline_2pl.yml',
            duration=DURATION,
            label='Baseline 2PL (Single-Node)'
        )
        
        # 2. Deterministic Single-Node
        runner.run_benchmark(
            'test_det.yml',
            duration=DURATION,
            label='Deterministic (Single-Node)'
        )
        
        # 3. Deterministic Multi-Node
        runner.run_benchmark(
            'test_det_multi.yml',
            duration=DURATION,
            label='Deterministic (Multi-Node, 3 replicas)'
        )
        
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.")
    except Exception as e:
        print(f"\n\nError during benchmarking: {e}")
    
    # Print summary and save results
    runner.print_summary()
    runner.save_results()
    
    print("\nBenchmark evaluation complete!")

if __name__ == '__main__':
    main()
