#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查PID文件是否存在
if [ ! -f logs/server.pid ]; then
    echo -e "${RED}Error: PID file not found. Server may not be running.${NC}"
    exit 1
fi

# 读取PID
PID=$(cat logs/server.pid)

# 检查进程是否存在
if ! ps -p $PID > /dev/null; then
    echo -e "${YELLOW}Warning: Process with PID $PID not found. Server may have crashed.${NC}"
    echo -e "${YELLOW}Removing stale PID file.${NC}"
    rm logs/server.pid
    exit 1
fi

# 停止服务
echo -e "${GREEN}Stopping AnythingAgent service with PID: $PID${NC}"
kill $PID

# 等待进程结束
echo -e "${GREEN}Waiting for process to terminate...${NC}"
for i in {1..10}; do
    if ! ps -p $PID > /dev/null; then
        echo -e "${GREEN}Process terminated successfully.${NC}"
        rm logs/server.pid
        exit 0
    fi
    sleep 1
done

# 如果进程仍然存在，强制终止
if ps -p $PID > /dev/null; then
    echo -e "${YELLOW}Process did not terminate gracefully. Forcing termination...${NC}"
    kill -9 $PID
    if ! ps -p $PID > /dev/null; then
        echo -e "${GREEN}Process terminated forcefully.${NC}"
        rm logs/server.pid
        exit 0
    else
        echo -e "${RED}Failed to terminate process.${NC}"
        exit 1
    fi
fi 