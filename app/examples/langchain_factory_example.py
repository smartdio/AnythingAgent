#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LangChainLLMFactory 使用示例
展示如何使用工厂模式创建和使用 LangChain LLM
"""

import asyncio
from typing import Dict, Any, Optional

# 导入 LangChainLLMFactory
from app.models.langchain_factory import LangChainLLMFactory

# 导入 LangChain 相关模块
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models.base import BaseLLM

async def openai_example_direct():
    """
    OpenAI 示例：直接使用 create_openai_llm 方法
    """
    print("=== OpenAI 示例 (直接方法) ===")
    
    # 直接使用 create_openai_llm 方法创建 LLM
    llm: Optional[BaseLLM] = LangChainLLMFactory.create_openai_llm(
        model="gpt-3.5-turbo",
        temperature=0.7,
        api_key="your-openai-api-key"  # 替换为您的 API 密钥
    )
    
    if not llm:
        print("LLM 创建失败，请检查配置")
        return
    
    # 创建消息
    messages = [
        SystemMessage(content="你是一个有用的AI助手。"),
        HumanMessage(content="你好，请介绍一下自己。")
    ]
    
    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages(messages)
    
    # 创建输出解析器
    output_parser = StrOutputParser()
    
    # 创建链
    chain = prompt | llm | output_parser
    
    # 调用 LLM
    print("正在调用 LLM...")
    response = await chain.ainvoke({})
    
    print(f"LLM 响应:\n{response}")
    print()

async def openai_example_generic():
    """
    OpenAI 示例：使用通用 create_llm 方法
    """
    print("=== OpenAI 示例 (通用方法) ===")
    
    # 使用通用 create_llm 方法创建 LLM
    llm: Optional[BaseLLM] = LangChainLLMFactory.create_llm(
        provider="openai",
        model="gpt-3.5-turbo",
        temperature=0.7,
        api_key="your-openai-api-key",  # 替换为您的 API 密钥
        api_base="https://api.openai.com/v1"  # 可选，自定义 API 端点
    )
    
    if not llm:
        print("LLM 创建失败，请检查配置")
        return
    
    # 创建消息
    messages = [
        SystemMessage(content="你是一个专业的Python开发者。"),
        HumanMessage(content="请写一个简单的Python函数，计算斐波那契数列。")
    ]
    
    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages(messages)
    
    # 创建输出解析器
    output_parser = StrOutputParser()
    
    # 创建链
    chain = prompt | llm | output_parser
    
    # 调用 LLM
    print("正在调用 LLM...")
    response = await chain.ainvoke({})
    
    print(f"LLM 响应:\n{response}")
    print()

async def anthropic_example():
    """
    Anthropic 示例：使用 Anthropic 模型
    """
    print("=== Anthropic 示例 ===")
    
    # 使用 create_anthropic_llm 方法创建 LLM
    llm: Optional[BaseLLM] = LangChainLLMFactory.create_anthropic_llm(
        model="claude-2",
        temperature=0.5,
        api_key="your-anthropic-api-key"  # 替换为您的 API 密钥
    )
    
    if not llm:
        print("LLM 创建失败，请检查配置")
        return
    
    # 创建消息
    messages = [
        SystemMessage(content="你是一个专业的数据科学家。"),
        HumanMessage(content="请解释一下随机森林算法的工作原理。")
    ]
    
    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages(messages)
    
    # 创建输出解析器
    output_parser = StrOutputParser()
    
    # 创建链
    chain = prompt | llm | output_parser
    
    # 调用 LLM
    print("正在调用 LLM...")
    response = await chain.ainvoke({})
    
    print(f"LLM 响应:\n{response}")
    print()

async def ollama_example():
    """
    Ollama 示例：使用本地 Ollama 模型
    """
    print("=== Ollama 示例 ===")
    
    # 使用 create_ollama_llm 方法创建 LLM
    llm: Optional[BaseLLM] = LangChainLLMFactory.create_ollama_llm(
        model="llama2",
        temperature=0.7,
        base_url="http://localhost:11434",  # Ollama 服务地址
        use_legacy=False  # 使用新版 OllamaLLM 接口
    )
    
    if not llm:
        print("LLM 创建失败，请检查配置")
        return
    
    # 创建消息
    messages = [
        SystemMessage(content="你是一个故事讲述者。"),
        HumanMessage(content="请用100字左右讲一个关于AI的短故事。")
    ]
    
    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages(messages)
    
    # 创建输出解析器
    output_parser = StrOutputParser()
    
    # 创建链
    chain = prompt | llm | output_parser
    
    # 流式调用 LLM
    print("正在流式调用 LLM...")
    
    # 模拟流式输出
    full_response = ""
    async for chunk in chain.astream({}, {"stream": True}):
        full_response += chunk
        print(chunk, end="", flush=True)
    
    print("\n\n流式输出完成")
    print()

async def ollama_legacy_example():
    """
    Ollama 示例：使用旧版 Ollama 接口
    """
    print("=== Ollama 示例 (旧版接口) ===")
    
    # 使用通用 create_llm 方法创建 LLM，指定使用旧版接口
    llm: Optional[BaseLLM] = LangChainLLMFactory.create_llm(
        provider="ollama",
        model="llama2",
        temperature=0.7,
        api_base="http://localhost:11434",  # Ollama 服务地址
        use_legacy=True  # 使用旧版 Ollama 接口
    )
    
    if not llm:
        print("LLM 创建失败，请检查配置")
        return
    
    # 创建消息
    messages = [
        SystemMessage(content="你是一个诗人。"),
        HumanMessage(content="请写一首关于人工智能的短诗。")
    ]
    
    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages(messages)
    
    # 创建输出解析器
    output_parser = StrOutputParser()
    
    # 创建链
    chain = prompt | llm | output_parser
    
    # 调用 LLM
    print("正在调用 LLM...")
    response = await chain.ainvoke({})
    
    print(f"LLM 响应:\n{response}")
    print()

async def main():
    """
    主函数
    """
    print("LangChainLLMFactory 使用示例")
    print("===========================")
    
    # 运行示例
    await openai_example_direct()
    await openai_example_generic()
    await anthropic_example()
    await ollama_example()
    await ollama_legacy_example()

if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main()) 