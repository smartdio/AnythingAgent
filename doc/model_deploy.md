# 模型的部署

AnythingAgent 支持基于目录的模型开发和部署方式。每个模型都是一个独立的目录，包含必要的文件和配置。

## 模型运行环境

AnythingAgent 提供两种模型运行模式：

### 1. 共享环境模式（默认）

默认情况下，所有模型都在主服务的 Python 环境中运行。这种模式：

- 优点：
  - 部署简单，无需额外配置
  - 资源占用少
  - 启动速度快
- 缺点：
  - 可能存在依赖冲突
  - 缺乏资源隔离
  - 安全性较低

适用场景：
- 内部开发和测试
- 可信任的模型
- 依赖简单的模型

### 2. 隔离环境模式（推荐）

通过在模型配置中指定 `isolation: true`，可以让模型在独立的虚拟环境中运行：

```yaml
# config.yaml
name: my_model
version: 1.0.0
# 启用环境隔离
isolation:
  enabled: true
  # 指定 Python 版本
  python_version: "3.10"
  # 资源限制
  resources:
    memory: "1G"
    cpu: 1
```

这种模式：
- 优点：
  - 完全的依赖隔离
  - 资源使用限制
  - 更高的安全性
- 缺点：
  - 部署较复杂
  - 资源开销较大
  - 启动时间较长

适用场景：
- 生产环境部署
- 第三方模型
- 有复杂依赖的模型

### 环境隔离实现

1. 创建虚拟环境：
```bash
# 在模型目录下创建虚拟环境
python -m venv venv

# 安装依赖
./venv/bin/pip install -r requirements.txt
```

2. 启动隔离进程：
```python
import subprocess
import sys

def run_isolated_model(model_dir: str, input_data: str) -> str:
    venv_python = f"{model_dir}/venv/bin/python"
    process = subprocess.Popen(
        [venv_python, "main.py"],
        cwd=model_dir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return process.communicate(input_data.encode())[0].decode()
```

3. 资源限制：
```python
import resource

def set_resource_limits(memory_mb: int):
    # 设置内存限制
    resource.setrlimit(
        resource.RLIMIT_AS,
        (memory_mb * 1024 * 1024, -1)
    )
```

## 模型目录结构

模型需要放在项目根目录下的 `models` 目录中（可通过 `MODELS_DIR` 配置修改）。每个模型都是该目录下的一个子目录：

```
models/                    # 模型根目录
├── test_model/           # 测试模型
│   ├── main.py          # 模型主程序（必需）
│   ├── config.yaml      # 配置文件（可选）
│   ├── requirements.txt # 依赖库（可选）
│   └── data/           # 数据目录（可选）
│       ├── vocab.txt
│       └── model.bin
└── other_model/         # 其他模型
    ├── main.py
    └── config.yaml
```

## 开发流程

1. 在 `models` 目录下创建新的模型目录
2. 开发模型文件（至少包含 `main.py`）
3. 添加配置文件和数据文件（可选）
4. 调用重新加载接口使模型生效

无需打包和部署步骤，开发完成后直接可用。

## 模型的主程序

模型的主程序 `main.py` 是一个 Python 文件，它定义了模型的核心功能。主程序需要：

1. 继承自 `AnythingBaseModel` 类
2. 实现必要的接口方法
3. 通过注释来描述模型的功能

示例：
```python
from app.models.base import AnythingBaseModel
from typing import List, Dict, Optional, AsyncGenerator

class MyModel(AnythingBaseModel):
    """
    这是一个示例模型。
    它演示了如何实现一个基本的模型。
    """
    
    async def on_chat_messages(
        self,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        # 访问配置
        parameters = self.config.get("parameters", {})
        temperature = parameters.get("temperature", 0.7)
        
        # 访问数据文件
        vocab_file = self.data_dir / "vocab.txt"
        if vocab_file.exists():
            vocab = vocab_file.read_text()
        
        # 流式输出响应
        yield "这是第一部分响应\n"
        yield "这是第二部分响应\n"
        yield "这是最后一部分响应"

    async def on_chat_start(self) -> None:
        """聊天开始时的钩子方法"""
        self.clear_context()
        
    async def on_chat_end(self) -> None:
        """聊天结束时的钩子方法"""
        self.clear_context()
```

## 配置文件

模型的配置文件 `config.yaml` 用于定义模型的参数和设置：

```yaml
# 模型基本信息
name: my_model
version: 1.0.0
description: 这是一个示例模型

# 模型参数
parameters:
  temperature: 0.7
  max_tokens: 1000
  top_p: 1.0
  
# 其他配置
settings:
  use_cache: true
  timeout: 30
```

## 依赖库

如果模型需要特定的依赖库，可以在 `requirements.txt` 文件中列出：

```
transformers==4.30.0
torch==2.0.0
numpy==1.24.0
```

## data 文件夹

`data` 文件夹用于存放模型运行时需要的数据文件，例如：
- 词表文件
- 预训练模型文件
- 配置文件
- 其他资源文件

模型可以通过 `self.data_dir` 属性访问数据目录。

## 流式响应实现

AnythingAgent 使用 AsyncGenerator 实现流式响应。这是一个更简单和直观的方式来处理流式输出：

```python
async def on_chat_messages(
    self,
    messages: List[Dict[str, str]]
) -> AsyncGenerator[str, None]:
    """
    处理聊天消息并返回流式响应
    
    Args:
        messages: 消息列表，每个消息是包含role和content的字典
        
    Yields:
        str: 响应的各个部分
    """
    # 处理用户消息
    last_message = messages[-1]["content"]
    
    # 生成多个部分的响应
    yield f"收到消息：{last_message}\n"
    yield "正在处理...\n"
    
    # 可以在处理过程中执行其他异步操作
    await asyncio.sleep(1)
    
    yield "处理完成！"
```

## 模型管理

### 1. 查看模型列表

```bash
curl http://localhost:8000/v1/models
```

### 2. 重新加载模型

在修改模型代码或配置后，需要重新加载才能生效：

```bash
curl -X POST http://localhost:8000/v1/models/reload
```

## 最佳实践

1. 模型命名
   - 使用小写字母和下划线
   - 避免使用特殊字符
   - 名称应该具有描述性

2. 配置管理
   - 将可变参数放在配置文件中
   - 使用有意义的默认值
   - 添加配置项的注释说明

3. 数据文件
   - 使用合适的文件格式
   - 添加版本信息
   - 考虑数据的可更新性

4. 错误处理
   - 优雅处理配置错误
   - 检查数据文件完整性
   - 提供有意义的错误信息

5. 文档
   - 在主程序中添加详细的文档字符串
   - 说明配置项的用途和取值范围
   - 提供使用示例

6. 流式响应
   - 合理分割响应内容
   - 及时返回初始响应
   - 处理异常情况

## 开发提示

1. 目录结构
   - 保持目录结构清晰
   - 相关文件放在适当的位置
   - 避免在模型目录中存放临时文件

2. 配置访问
   - 使用 `self.config.get("parameters", {})` 获取参数配置
   - 为所有参数提供合理的默认值
   - 记录配置项的变更

3. 数据文件访问
   - 使用 `self.data_dir` 访问数据目录
   - 检查文件是否存在
   - 正确处理文件读取错误

4. 开发流程
   - 在开发环境中直接修改模型文件
   - 修改后调用 reload 接口重新加载
   - 使用日志记录调试信息

5. 流式响应开发
   - 使用 AsyncGenerator 实现流式输出
   - 合理控制每个部分的大小
   - 注意异常处理和资源释放