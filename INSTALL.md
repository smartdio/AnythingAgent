# AnythingAgent 安装指南

## 环境要求

- Python 3.11 或更高版本
- 推荐使用 Conda 进行环境管理

## 使用 Conda 安装（推荐）

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/AnythingAgent.git
cd AnythingAgent
```

2. 使用 environment.yml 创建环境：

```bash
conda env create -f environment.yml
```

3. 激活环境：

```bash
conda activate aagent
```

## 使用 pip 安装

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/AnythingAgent.git
cd AnythingAgent
```

2. 创建虚拟环境（可选但推荐）：

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

## 验证安装

安装完成后，可以运行以下命令验证安装是否成功：

```bash
python -c "import fastapi; import uvicorn; import pydantic; import lancedb; print('安装成功！')"
```

## 启动服务

### 前台运行（开发模式）

```bash
./start.sh
```

服务启动后，可以访问 http://localhost:8000/docs 查看 API 文档。

### 后台运行（生产模式）

```bash
# 使用默认日志文件 logs/server.log
./start.sh --daemon

# 或指定自定义日志文件
./start.sh --daemon --log-file /path/to/custom/logfile.log
```

### 管理后台服务

```bash
# 检查服务状态
./status.sh

# 停止服务
./stop.sh
```

## 环境变量配置

可以通过环境变量自定义服务配置：

```bash
# 自定义主机和端口
HOST=127.0.0.1 PORT=9000 ./start.sh

# 生产环境模式（禁用热重载，增加工作进程）
ENV=production ./start.sh

# 自定义工作进程数量
WORKERS=2 ./start.sh

# 自定义日志级别
LOG_LEVEL=debug ./start.sh
```

## 常见问题

1. **LanceDB 安装问题**：如果 LanceDB 安装失败，请确保系统已安装 Rust 编译器。

2. **依赖冲突**：如果遇到依赖冲突，建议使用 Conda 环境，它可以更好地处理依赖关系。

3. **litellm 配置**：确保在使用前正确配置 API 密钥。

4. **后台运行问题**：如果后台运行的服务无法正常停止，可以使用 `ps aux | grep uvicorn` 查找进程 ID，然后使用 `kill -9 <PID>` 强制终止。 