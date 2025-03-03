# LangChain 分析器模型

基于 LangChain 的深度分析模型，支持多种任务处理和上下文管理。

## 功能特点

- 使用 LangChain 进行 LLM 调用
- 支持多种 LLM 提供商（OpenAI、Anthropic、Azure、Ollama）
- 支持流式输出
- 支持任务管理和分析
- 支持上下文管理
- 支持向量搜索

## 安装依赖

```bash
pip install langchain langchain-openai langchain-anthropic langchain-community langchain-azure
```

## 使用方法

### 基本使用

```python
from app.models.langchain_analyzer import LangChainAnalyzerModel

# 初始化模型
model = LangChainAnalyzerModel()

# 处理聊天消息
async def handle_message(message):
    response = await model.on_chat_messages([
        {"role": "system", "content": "你是一个有用的助手"},
        {"role": "user", "content": message}
    ])
    print(response)

# 使用流式输出
async def handle_stream(message):
    async def callback(chunk):
        print(chunk, end="", flush=True)
    
    await model.on_chat_messages([
        {"role": "system", "content": "你是一个有用的助手"},
        {"role": "user", "content": message}
    ], callback=callback)
```

### 分析任务

使用 `/analyze` 命令进行深度分析：

```
/analyze 分析全球气候变化对农业生产的影响
```

### 任务管理

使用 `/task` 命令管理任务：

```
/task add 研究人工智能对就业市场的影响
/task list
/task execute 1
/task executeall
/task clear
```

### 切换 LLM 配置

```python
# 切换到创意模式（使用 Claude）
model.set_llm("creative")

# 切换到快速模式（使用 GPT-3.5）
model.set_llm("fast")

# 切换到本地模式（使用 Ollama）
model.set_llm("local")

# 切换回默认模式
model.set_llm("default")
```

### 上下文管理

```python
# 更新上下文
await model.on_context_update({
    "user_info": {
        "name": "张三",
        "interests": ["AI", "编程", "音乐"]
    }
})

# 清除上下文
await model.on_context_clear()
```

### 向量搜索

```python
# 执行向量搜索
results = await model.on_vector_search("人工智能的发展历程", top_k=5)
```

## 配置文件

模型可以通过 `config.yaml` 文件进行配置，示例配置见 `config_example.yaml`。

## 环境变量

可以通过环境变量配置 LLM：

- `LLM_PROVIDER`: LLM提供商 (openai, anthropic, azure, ollama)
- `LLM_MODEL`: 模型名称
- `LLM_TEMPERATURE`: 温度参数
- `LLM_API_KEY`: API密钥
- `LLM_API_BASE`: API基础URL

也支持特定提供商的环境变量：

- OpenAI: `OPENAI_API_KEY`, `OPENAI_API_BASE`
- Anthropic: `ANTHROPIC_API_KEY`, `ANTHROPIC_API_BASE`
- Azure: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`
- Ollama: `OLLAMA_API_BASE` 