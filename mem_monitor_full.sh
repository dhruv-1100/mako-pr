#!/bin/bash
LOGFILE="res_usage_alert.log"
MEM_THRESHOLD=8000000   # KB, adjust as needed (e.g., 8GB)
echo "Time, PID, Process, %CPU, %MEM, RSS(KB), VSZ(KB), Threads, TotalMem(KB), UsedMem(KB), FreeMem(KB), SwapUsed(KB), ALERT" > "$LOGFILE"

while true; do
    read total used free <<< $(free -k | awk '/^Mem:/ {print $2, $3, $4}')
    read swapused <<< $(free -k | awk '/^Swap:/ {print $3}')
    
    ps -e -o pid,comm,%cpu,%mem,rss,vsz,nlwp --sort=-%mem | grep -E 'dbtest|shard.sh' | grep -v grep | \
    while read pid comm cpu mem rss vsz threads; do
        alert=""
        if [ "$rss" -ge "$MEM_THRESHOLD" ]; then
            alert="MEMORY_SPIKE"
        fi
        echo "$(date +"%F %T"),$pid,$comm,$cpu,$mem,$rss,$vsz,$threads,$total,$used,$free,$swapused,$alert" >> "$LOGFILE"
    done

    sleep 1
done

