#!/bin/bash
# Monitor study resource usage in real-time

echo "Monitoring Solstice study resources..."
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    echo "=== SOLSTICE STUDY MONITOR ==="
    echo "Time: $(date '+%H:%M:%S')"
    echo ""
    
    # Memory usage
    echo "📊 MEMORY USAGE:"
    ps aux | grep -E "python.*run[-_]study" | grep -v grep | while read line; do
        PID=$(echo $line | awk '{print $2}')
        MEM=$(echo $line | awk '{print $6/1024}')
        CPU=$(echo $line | awk '{print $3}')
        echo "  PID $PID: ${MEM}MB RAM, ${CPU}% CPU"
    done
    
    # Total Python memory
    TOTAL_MEM=$(ps aux | grep -E "python.*run[-_]study" | grep -v grep | awk '{sum+=$6} END {print sum/1024}')
    echo "  Total Python: ${TOTAL_MEM:-0}MB"
    
    # System memory
    echo ""
    echo "📈 SYSTEM RESOURCES:"
    vm_stat | grep -E "(free:|wired:|active:|inactive:)" | sed 's/Pages //' | awk '{print "  " $1 " " $2*4096/1024/1024 " MB"}'
    
    # Network connections to gateway
    echo ""
    echo "🌐 GATEWAY CONNECTIONS:"
    netstat -an | grep -E "localhost:(8000|8080).*ESTABLISHED" | wc -l | awk '{print "  Active connections: " $1}'
    
    # Check for errors in recent logs
    echo ""
    echo "❌ RECENT ERRORS:"
    tail -n 1000 ~/.solstice/logs/*.log 2>/dev/null | grep -i "error\|failed\|timeout" | tail -n 3 | sed 's/^/  /'
    
    sleep 2
done