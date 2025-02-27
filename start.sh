#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查是否存在 .env 文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copying from .env_example...${NC}"
    if [ -f .env_example ]; then
        cp .env_example .env
        echo -e "${GREEN}Created .env file from .env_example${NC}"
    else
        echo -e "${RED}Error: .env_example file not found${NC}"
        exit 1
    fi
fi

# 检查 conda 是否安装
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: Conda is not installed${NC}"
    exit 1
fi

# 初始化 conda
CONDA_PATH=$(conda info --base)
source "${CONDA_PATH}/etc/profile.d/conda.sh"

# 检查并激活 conda 环境
if ! conda env list | grep -q "aagent"; then
    echo -e "${YELLOW}Creating new conda environment 'aagent'...${NC}"
    conda create -n aagent python=3.10 -y
fi

echo -e "${GREEN}Activating conda environment 'aagent'...${NC}"
conda activate aagent

# 安装依赖
if command -v poetry &> /dev/null; then
    echo -e "${GREEN}Installing dependencies using Poetry...${NC}"
    poetry install
else
    echo -e "${YELLOW}Poetry not found, using pip to install dependencies...${NC}"
    pip install -r requirements.txt
fi

# 设置环境变量
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 启动参数
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-8000}
WORKERS=${WORKERS:-1}
LOG_LEVEL=${LOG_LEVEL:-"info"}
RELOAD=${RELOAD:-"--reload"}

# 检查是否是生产环境
if [ "$ENV" = "production" ]; then
    RELOAD=""
    WORKERS=4
    LOG_LEVEL="error"
fi

# 创建日志目录
mkdir -p logs

# 启动服务
echo -e "${GREEN}Starting AnythingAgent service...${NC}"
echo -e "${GREEN}Host: $HOST${NC}"
echo -e "${GREEN}Port: $PORT${NC}"
echo -e "${GREEN}Workers: $WORKERS${NC}"
echo -e "${GREEN}Log Level: $LOG_LEVEL${NC}"

# 转换日志级别为小写
LOG_LEVEL=$(echo "$LOG_LEVEL" | tr '[:upper:]' '[:lower:]')

uvicorn app.main:app \
    --host $HOST \
    --port $PORT \
    --workers $WORKERS \
    --log-level $LOG_LEVEL \
    $RELOAD \
    --log-config logging_config.json 