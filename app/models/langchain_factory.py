#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LangChain LLM工厂
用于创建LangChain LLM实例
"""

import logging
from typing import Dict, Any, Optional, Union, Literal

# 设置日志
logger = logging.getLogger(__name__)

# 导入 LangChain 相关模块
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import OllamaLLM
from langchain_community.llms import Ollama
from langchain_core.language_models.llms import BaseLLM

class LangChainLLMFactory:
    """
    LangChainLLMFactory 负责创建 LLM 模型实例。
    根据传递的参数直接创建并返回 LangChain LLM 实例。
    
    支持的 LLM 提供商:
    - OpenAI (ChatGPT)
    - Anthropic (Claude)
    - Ollama (本地模型)
    
    所有方法返回的都是 BaseLLM 类型的实例，确保类型一致性。
    """
    
    @staticmethod
    def create_openai_llm(
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        api_key: str = "",
        api_base: Optional[str] = None,
        **kwargs
    ) -> Optional[BaseLLM]:
            
        try:
            llm_kwargs = {
                "model": model,
                "temperature": temperature,
                "openai_api_key": api_key,
                **kwargs
            }
            
            if api_base:
                llm_kwargs["openai_api_base"] = api_base
                
            return ChatOpenAI(**llm_kwargs)
        except Exception as e:
            logger.error(f"创建 OpenAI LLM 时出错: {str(e)}")
            return None
    
    @staticmethod
    def create_anthropic_llm(
        model: str = "claude-2",
        temperature: float = 0.7,
        api_key: str = "",
        **kwargs
    ) -> Optional[BaseLLM]:
        if not api_key:
            logger.error("未提供 Anthropic API Key")
            return None
            
        try:
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                anthropic_api_key=api_key,
                **kwargs
            )
        except Exception as e:
            logger.error(f"创建 Anthropic LLM 时出错: {str(e)}")
            return None
    
    @staticmethod
    def create_ollama_llm(
        model: str = "llama2",
        temperature: float = 0.7,
        base_url: str = "http://localhost:11434",
        use_legacy: bool = False,
        **kwargs
    ) -> Optional[BaseLLM]:
        try:
            # 根据参数选择使用哪个 Ollama 实现
            if use_legacy:
                return Ollama(
                    model=model,
                    temperature=temperature,
                    base_url=base_url,
                    **kwargs
                )
            else:
                return OllamaLLM(
                    model=model,
                    temperature=temperature,
                    base_url=base_url,
                    **kwargs
                )
        except Exception as e:
            logger.error(f"创建 Ollama LLM 时出错: {str(e)}")
            return None
    
    @staticmethod
    def create_llm(
        provider: Literal["openai", "anthropic", "ollama"],
        model: str,
        temperature: float = 0.7,
        api_key: str = "",
        api_base: Optional[str] = None,
        use_legacy: bool = False,
        **kwargs
    ) -> Optional[BaseLLM]:
        # 构建基本参数
        base_params = {
            "model": model,
            "temperature": temperature,
        }
        
        # 根据提供商添加特定参数
        if provider == "openai":
            if api_key:
                base_params["api_key"] = api_key
            if api_base:
                base_params["api_base"] = api_base
            return LangChainLLMFactory.create_openai_llm(**base_params, **kwargs)
            
        elif provider == "anthropic":
            if api_key:
                base_params["api_key"] = api_key
            return LangChainLLMFactory.create_anthropic_llm(**base_params, **kwargs)
            
        elif provider == "ollama":
            if api_base:
                base_params["base_url"] = api_base
            base_params["use_legacy"] = use_legacy
            return LangChainLLMFactory.create_ollama_llm(**base_params, **kwargs)
            
        else:
            logger.error(f"不支持的 LLM 提供商: {provider}")
            return None 