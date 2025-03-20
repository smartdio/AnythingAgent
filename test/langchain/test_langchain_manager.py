#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试LangChainLLMManager初始化
"""

import os
import sys
import logging
from pathlib import Path

# 设置日志级别
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 添加项目根目录到Python路径
current_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(current_dir))

# 导入LangChainLLMManager
try:
    from app.models.langchain_factory import LangChainLLMManager, LANGCHAIN_AVAILABLE
    print(f"✅ 成功导入 LangChainLLMManager")
    print(f"LANGCHAIN_AVAILABLE = {LANGCHAIN_AVAILABLE}")
except ImportError as e:
    print(f"❌ 导入失败 LangChainLLMManager: {str(e)}")
    sys.exit(1)

async def test_manager():
    """测试LangChainLLMManager初始化"""
    try:
        # 创建LangChainLLMManager实例
        manager = LangChainLLMManager()
        print(f"✅ 成功创建 LangChainLLMManager 实例")
        
        # 检查llm_config是否为None
        print(f"llm_config = {manager.llm_config}")
        print(f"llm = {manager.llm}")
        
        # 尝试初始化LLM
        if os.environ.get("OPENAI_API_KEY"):
            config = {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7
            }
            success = manager._init_llm()
            print(f"✅ 初始化LLM结果: {success}")
            print(f"llm_config = {manager.llm_config}")
            print(f"llm = {manager.llm}")
        else:
            print("⚠️ 未设置OPENAI_API_KEY环境变量，跳过LLM初始化测试")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_manager())
    if result:
        print("\n✅ 测试通过")
    else:
        print("\n❌ 测试失败")
        sys.exit(1) 