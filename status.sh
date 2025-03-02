#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查PID文件是否存在
if [ ! -f logs/server.pid ]; then
    echo -e "${YELLOW}AnythingAgent service is not running (no PID file found).${NC}"
    exit 1
fi

# 读取PID
PID=$(cat logs/server.pid)

# 检查进程是否存在
if ! ps -p $PID > /dev/null; then
    echo -e "${RED}AnythingAgent service is not running (PID $PID not found).${NC}"
    echo -e "${YELLOW}PID file exists but process is not running. Server may have crashed.${NC}"
    echo -e "${YELLOW}Consider removing the stale PID file: rm logs/server.pid${NC}"
    exit 1
fi

# 获取进程信息
PROCESS_INFO=$(ps -p $PID -o pid,ppid,user,%cpu,%mem,start,etime,command | tail -n 1)

# 获取端口信息
PORT_INFO=$(netstat -tuln 2>/dev/null | grep -E "LISTEN.*:8000" || echo "Port information not available")

# 显示状态信息
echo -e "${GREEN}AnythingAgent service is running with PID: $PID${NC}"
echo -e "${GREEN}Process information:${NC}"
echo -e "${GREEN}$(ps -p $PID -o pid,ppid,user,%cpu,%mem,start,etime | head -n 1)${NC}"
echo -e "${GREEN}$PROCESS_INFO${NC}"
echo -e "\n${GREEN}Port information:${NC}"
echo -e "${GREEN}$PORT_INFO${NC}"

# 检查日志文件
if [ -f logs/server.log ]; then
    LOG_SIZE=$(du -h logs/server.log | cut -f1)
    LAST_MODIFIED=$(stat -f "%Sm" logs/server.log)
    echo -e "\n${GREEN}Log file information:${NC}"
    echo -e "${GREEN}Size: $LOG_SIZE${NC}"
    echo -e "${GREEN}Last modified: $LAST_MODIFIED${NC}"
    echo -e "${GREEN}Last 5 log entries:${NC}"
    echo -e "${YELLOW}$(tail -n 5 logs/server.log)${NC}"
fi

exit 0 