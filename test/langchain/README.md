# LangChain 测试

本目录包含与 LangChain 相关的测试文件。

## 测试文件

1. `test_langchain_imports.py` - 测试 LangChain 相关模块的导入情况
2. `test_langchain_manager.py` - 测试 `LangChainLLMManager` 的初始化和基本功能

## 运行测试

确保在 `aagent` conda 环境中运行测试：

```bash
# 激活环境
conda activate aagent

# 运行导入测试
python test/langchain/test_langchain_imports.py

# 运行管理器测试
python test/langchain/test_langchain_manager.py
```

## 测试结果

如果测试成功，将显示类似以下输出：

```
✅ 成功导入 langchain_core.prompts
✅ 成功导入 langchain_core.output_parsers
✅ 成功导入 langchain_core.messages
✅ 成功导入 langchain_openai
✅ 成功导入 langchain_anthropic
✅ 成功导入 langchain_community.llms
✅ 成功导入 langchain_core.runnables

总结: 成功导入 7/7 个模块
```

以及：

```
✅ 成功导入 LangChainLLMManager
LANGCHAIN_AVAILABLE = True
✅ 成功创建 LangChainLLMManager 实例
llm_config = {...}
llm = None
⚠️ 未设置OPENAI_API_KEY环境变量，跳过LLM初始化测试

✅ 测试通过
``` 