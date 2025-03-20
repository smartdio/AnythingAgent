import asyncio
import os
import sys
from app.models.langchain_analyzer.main import LangChainAnalyzerModel

# 设置环境变量，禁用langchain的verbose和debug模式
os.environ["LANGCHAIN_VERBOSE"] = "false"
os.environ["LANGCHAIN_DEBUG"] = "false"

# 模拟langchain模块，添加verbose和debug属性
import types

if 'langchain' not in sys.modules:
    langchain_module = types.ModuleType('langchain')
    langchain_module.verbose = False
    langchain_module.debug = False
    # 添加llm_cache属性
    llm_cache_module = types.ModuleType('llm_cache')
    langchain_module.llm_cache = llm_cache_module
    sys.modules['langchain'] = langchain_module
else:
    # 如果已经导入了langchain模块，添加缺失的属性
    if not hasattr(sys.modules['langchain'], 'verbose'):
        sys.modules['langchain'].verbose = False
    if not hasattr(sys.modules['langchain'], 'debug'):
        sys.modules['langchain'].debug = False
    if not hasattr(sys.modules['langchain'], 'llm_cache'):
        llm_cache_module = types.ModuleType('llm_cache')
        sys.modules['langchain'].llm_cache = llm_cache_module

async def stream_callback(content: str) -> None:
    """流式输出回调函数"""
    print(f"流式输出: {content}", end="", flush=True)

async def test():
    # 初始化模型
    model = LangChainAnalyzerModel()
    
    # 准备测试消息 - 使用更复杂的查询
    messages = [{'role': 'user', 'content': '请帮我分析人工智能在医疗领域的应用现状和未来发展趋势，包括诊断、治疗和药物研发等方面'}]
    
    # 调用模型处理消息，使用流式输出
    print("\n开始流式输出测试:")
    result = await model.on_chat_messages(messages, callback=stream_callback)
    
    # 打印最终结果
    print("\n\n最终结果:", result[:100] + "..." if result and len(result) > 100 else result)

if __name__ == "__main__":
    asyncio.run(test()) 