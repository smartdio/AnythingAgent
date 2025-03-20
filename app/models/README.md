# LangChain LLM Factory

一个简单的工厂模式实现，用于创建 LangChain LLM 实例。

## 特点

- 简单的工厂模式，用于创建 LangChain LLM 实例
- 支持多种 LLM 提供商:
  - OpenAI (ChatGPT)
  - Anthropic (Claude)
  - Ollama (本地模型)
- 提供特定提供商的创建方法和通用创建方法
- 所有方法返回统一的 BaseLLM 类型，确保类型一致性

## 使用方法

### 特定提供商方法

#### OpenAI

```python
from app.models.langchain_manager import LangChainLLMFactory
from langchain_core.language_models.base import BaseLLM

# 创建 OpenAI LLM
llm: BaseLLM = LangChainLLMFactory.create_openai_llm(
    model="gpt-3.5-turbo",
    temperature=0.7,
    api_key="your-openai-api-key",
    api_base="https://api.openai.com/v1"  # 可选
)
```

#### Anthropic

```python
# 创建 Anthropic LLM
llm: BaseLLM = LangChainLLMFactory.create_anthropic_llm(
    model="claude-2",
    temperature=0.5,
    api_key="your-anthropic-api-key"
)
```

#### Ollama

```python
# 创建 Ollama LLM (使用新版接口)
llm: BaseLLM = LangChainLLMFactory.create_ollama_llm(
    model="llama2",
    temperature=0.7,
    base_url="http://localhost:11434",
    use_legacy=False  # 默认值，使用新版 OllamaLLM 接口
)

# 创建 Ollama LLM (使用旧版接口)
llm: BaseLLM = LangChainLLMFactory.create_ollama_llm(
    model="llama2",
    temperature=0.7,
    base_url="http://localhost:11434",
    use_legacy=True  # 使用旧版 Ollama 接口
)
```

### 通用方法

```python
# 使用通用方法创建 OpenAI LLM
llm: BaseLLM = LangChainLLMFactory.create_llm(
    provider="openai",
    model="gpt-3.5-turbo",
    temperature=0.7,
    api_key="your-openai-api-key",
    api_base="https://api.openai.com/v1"  # 可选
)

# 创建 Anthropic LLM
llm: BaseLLM = LangChainLLMFactory.create_llm(
    provider="anthropic",
    model="claude-2",
    temperature=0.5,
    api_key="your-anthropic-api-key"
)

# 创建 Ollama LLM 并指定使用旧版接口
llm: BaseLLM = LangChainLLMFactory.create_llm(
    provider="ollama",
    model="llama2",
    temperature=0.7,
    api_base="http://localhost:11434",
    use_legacy=True
)
```

### 使用 LLM

```python
# 使用 LangChain 调用 LLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Hello, introduce yourself.")
]
prompt = ChatPromptTemplate.from_messages(messages)
chain = prompt | llm | StrOutputParser()
response = await chain.ainvoke({})
```

## 返回类型

所有工厂方法都返回 `langchain_core.language_models.base.BaseLLM` 类型的实例，这是 LangChain 中所有 LLM 的基类。这确保了类型一致性，使得不同提供商的 LLM 可以以相同的方式使用。

如果创建失败，方法将返回 `None`。

## 示例

查看 `app/examples/langchain_factory_example.py` 获取完整的使用示例。

## 依赖

- langchain_core
- langchain_openai (用于 OpenAI 模型)
- langchain_anthropic (用于 Anthropic 模型)
- langchain_ollama (用于 Ollama 模型) 