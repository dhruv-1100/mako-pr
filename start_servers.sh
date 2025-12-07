#!/bin/bash
mkdir -p log
./build/deptran_server -b -f /tmp/test_1p_3rep.yml -P s1_proc -p 19101 -d 10 -r -t 10 > /tmp/server_0.log 2>&1 &
./build/deptran_server -b -f /tmp/test_1p_3rep.yml -P s2_proc -p 19102 -d 10 -r -t 10 > /tmp/server_1.log 2>&1 &
./build/deptran_server -b -f /tmp/test_1p_3rep.yml -P s3_proc -p 19103 -d 10 -r -t 10 > /tmp/server_2.log 2>&1 &
echo "Servers started."
