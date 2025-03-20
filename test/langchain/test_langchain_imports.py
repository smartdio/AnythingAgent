#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试langchain模块导入
"""

import sys
import importlib
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(current_dir))

def test_import(module_name):
    try:
        module = importlib.import_module(module_name)
        print(f"✅ 成功导入 {module_name}")
        return True
    except ImportError as e:
        print(f"❌ 导入失败 {module_name}: {str(e)}")
        return False

if __name__ == "__main__":
    modules_to_test = [
        "langchain_core.prompts",
        "langchain_core.output_parsers",
        "langchain_core.messages",
        "langchain_openai",
        "langchain_anthropic",
        "langchain_community.llms",
        "langchain_core.runnables"
    ]
    
    success_count = 0
    for module in modules_to_test:
        if test_import(module):
            success_count += 1
    
    print(f"\n总结: 成功导入 {success_count}/{len(modules_to_test)} 个模块")
    
    if success_count < len(modules_to_test):
        print("\n可能需要安装以下包:")
        print("pip install langchain-core langchain-openai langchain-anthropic langchain-community") 