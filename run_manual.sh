#!/bin/bash
./build/deptran_server -b -d 10 -f test_det_3replicas.yml -P s1_proc -p 18101 -t 10 > s1.log 2>&1 &
./build/deptran_server -b -d 10 -f test_det_3replicas.yml -P s2_proc -p 18102 -t 10 > s2.log 2>&1 &
./build/deptran_server -b -d 10 -f test_det_3replicas.yml -P s3_proc -p 18103 -t 10 > s3.log 2>&1 &
sleep 2
./build/deptran_server -b -d 10 -f test_det_3replicas.yml -P c1_proc -p 18100 -t 10 > c1.log 2>&1 &
wait
