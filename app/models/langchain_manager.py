#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LangChain LLM管理器
用于管理和调用LangChain LLM接口
"""

import os
import sys
import yaml
import json
import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable
from pathlib import Path
from dotenv import load_dotenv

# 设置日志
logger = logging.getLogger(__name__)

# 尝试导入langchain相关模块，如果不存在则设置为None
LANGCHAIN_AVAILABLE = True
IMPORT_ERROR_MSG = ""

try:
    from langchain_core.prompts import ChatPromptTemplate
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    IMPORT_ERROR_MSG = f"无法导入 langchain_core.prompts: {str(e)}"

try:
    from langchain_core.output_parsers import StrOutputParser
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    IMPORT_ERROR_MSG = f"无法导入 langchain_core.output_parsers: {str(e)}"

try:
    from langchain_core.messages import SystemMessage, HumanMessage
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    IMPORT_ERROR_MSG = f"无法导入 langchain_core.messages: {str(e)}"

try:
    from langchain_openai import ChatOpenAI
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    IMPORT_ERROR_MSG = f"无法导入 langchain_openai: {str(e)}"

try:
    from langchain_anthropic import ChatAnthropic
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    IMPORT_ERROR_MSG = f"无法导入 langchain_anthropic: {str(e)}"

try:
    from langchain_community.llms import Ollama
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    IMPORT_ERROR_MSG = f"无法导入 langchain_community.llms: {str(e)}"

# 不再尝试导入 StreamingResponse，我们将使用自定义的流式处理方法

if not LANGCHAIN_AVAILABLE:
    logger.error(f"LangChain 导入错误: {IMPORT_ERROR_MSG}")
else:
    logger.info("LangChain 模块导入成功")

class LangChainLLMManager:
    """
    LangChainLLMManager 负责 LLM 模型的加载、管理和调用功能。
    提供了基于 Langchain 的 LLM 管理功能，包括配置加载、环境变量处理和 LLM 调用。
    
    支持的 LLM 提供商:
    - OpenAI (ChatGPT)
    - Anthropic (Claude)
    - Ollama (本地模型)
    
    配置方式:
    1. 通过配置文件 (config.yaml)
    2. 通过环境变量
    3. 通过 .env 文件
    
    环境变量:
    - LLM_PROVIDER: LLM提供商 (openai, anthropic, ollama)
    - LLM_MODEL: 模型名称
    - LLM_TEMPERATURE: 温度参数
    - LLM_API_KEY: API密钥
    - LLM_API_BASE: API基础URL
    
    提供商特定环境变量:
    - OpenAI: OPENAI_API_KEY, OPENAI_API_BASE
    - Anthropic: ANTHROPIC_API_KEY, ANTHROPIC_API_BASE
    - Ollama: OLLAMA_API_BASE
    """
    
    def __init__(self, model_dir: Optional[Path] = None, config: Optional[Dict[str, Any]] = None):
        """
        初始化 LangChainLLMManager
        
        Args:
            model_dir: 模型目录路径，用于加载配置文件
            config: 模型配置，如果提供则优先使用
        """
        # 加载环境变量
        load_dotenv()
        
        self.model_dir = model_dir
        self.config = config or {}  # 模型配置
        self.llm_config = None  # LLM配置
        self.debug_file = None  # 调试文件
        self.llm = None  # Langchain LLM实例
        self.provider = ""  # 当前使用的提供商
        self.model = ""  # 当前使用的模型
        
        # 如果没有提供配置，尝试从模型目录加载
        if not config and model_dir:
            self._load_config()
        
        # 初始化LLM配置
        self._init_llm()
        
        # 初始化调试文件
        self._init_debug_file()
    
    def _load_config(self):
        """加载模型配置"""
        if self.model_dir and (self.model_dir / "config.yaml").exists():
            try:
                with open(self.model_dir / "config.yaml", 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                    logger.debug(f"加载配置: {self.config}")
            except Exception as e:
                logger.error(f"加载配置文件时出错: {str(e)}")
                self.config = {}
    
    def _init_llm(self) -> None:
        """
        初始化LLM配置，从配置文件、环境变量或.env文件中获取
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("langchain相关模块未安装，LLM功能将不可用")
            return
            
        try:
            # 获取LLM配置
            llm_config = self.config.get("llm", {}).get("default", {})
            
            # 从环境变量获取配置（优先级高于配置文件）
            provider = os.environ.get("LLM_PROVIDER", llm_config.get("provider", "openai")).lower()
            model = os.environ.get("LLM_MODEL", llm_config.get("model", "gpt-4"))
            temperature = float(os.environ.get("LLM_TEMPERATURE", llm_config.get("temperature", 0.7)))
            api_key = os.environ.get("LLM_API_KEY", llm_config.get("api_key", ""))
            api_base = os.environ.get("LLM_API_BASE", llm_config.get("api_base", ""))
            
            # 如果没有提供API密钥，尝试从特定环境变量获取
            if not api_key:
                if provider == "openai":
                    api_key = os.environ.get("OPENAI_API_KEY", "")
                elif provider == "anthropic":
                    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            
            # 如果没有提供API基础URL，尝试从特定环境变量获取
            if not api_base:
                if provider == "openai":
                    api_base = os.environ.get("OPENAI_API_BASE", "")
                elif provider == "anthropic":
                    api_base = os.environ.get("ANTHROPIC_API_BASE", "")
                elif provider == "ollama":
                    api_base = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
            
            # 构建LLM配置
            self.llm_config = {
                "provider": provider,
                "model": model,
                "temperature": temperature,
                "api_key": api_key,
                "api_base": api_base
            }
            
            # 初始化Langchain LLM实例
            self._initialize_langchain_llm()
            
            # 保存当前提供商和模型信息
            self.provider = provider
            self.model = model
            
            logger.info(f"已初始化LLM配置: {provider}/{model}")
            
        except Exception as e:
            logger.error(f"初始化LLM配置时出错: {str(e)}")
            self.llm_config = None
            self.llm = None
    
    def _initialize_langchain_llm(self) -> None:
        """
        初始化 Langchain LLM
        根据配置初始化不同的 LLM 提供商
        """
        if not LANGCHAIN_AVAILABLE:
            logger.error("Langchain 相关模块未安装，无法初始化 LLM")
            return
            
        try:
            provider = self.llm_config.get("provider", "").lower()
            self.provider = provider
            self.model = self.llm_config.get("model", "")
            
            # 记录初始化信息
            logger.info(f"初始化 Langchain LLM: provider={provider}, model={self.model}")
            self._write_debug(f"初始化 Langchain LLM: provider={provider}, model={self.model}")
            
            # 根据提供商初始化不同的 LLM
            if provider == "openai":
                # OpenAI
                api_key = self.llm_config.get("api_key") or os.getenv("OPENAI_API_KEY")
                api_base = self.llm_config.get("api_base") or os.getenv("OPENAI_API_BASE")
                
                if not api_key:
                    logger.error("OpenAI API Key 未设置")
                    return
                    
                kwargs = {
                    "model": self.model,
                    "temperature": self.llm_config.get("temperature", 0.7),
                    "openai_api_key": api_key,
                }
                
                if api_base:
                    kwargs["openai_api_base"] = api_base
                    
                self.llm = ChatOpenAI(**kwargs)
                logger.info(f"已初始化 OpenAI LLM: {self.model}")
                
            elif provider == "anthropic":
                # Anthropic
                api_key = self.llm_config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
                
                if not api_key:
                    logger.error("Anthropic API Key 未设置")
                    return
                    
                self.llm = ChatAnthropic(
                    model=self.model,
                    temperature=self.llm_config.get("temperature", 0.7),
                    anthropic_api_key=api_key
                )
                logger.info(f"已初始化 Anthropic LLM: {self.model}")
                
            elif provider == "ollama":
                # Ollama
                # 从api_base或base_url参数中获取基础URL
                base_url = self.llm_config.get("base_url") or self.llm_config.get("api_base") or "http://localhost:11434"
                
                self.llm = Ollama(
                    model=self.model,
                    temperature=self.llm_config.get("temperature", 0.7),
                    base_url=base_url
                )
                logger.info(f"已初始化 Ollama LLM: {self.model}, base_url: {base_url}")
                
            else:
                logger.error(f"不支持的 LLM 提供商: {provider}")
                
        except Exception as e:
            logger.error(f"初始化 Langchain LLM 时出错: {str(e)}")
            self._write_debug(f"初始化 Langchain LLM 时出错: {str(e)}")
            self.llm = None
    
    def _init_debug_file(self) -> None:
        """
        初始化调试文件
        """
        try:
            # 检查是否启用调试
            debug_enabled = os.environ.get("DEBUG_ENABLED", "").lower() in ["true", "1", "yes"]
            if not debug_enabled and not self.config.get("debug", {}).get("enabled", False):
                return
                
            debug_dir = Path(os.environ.get("DEBUG_DIR", "debug_logs"))
            debug_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            model_name = "langchain"
            self.debug_file = debug_dir / f"{model_name}_debug_{timestamp}.log"
            
            # 写入初始信息
            with open(self.debug_file, "w", encoding="utf-8") as f:
                f.write(f"=== LangChain 调试日志 - {timestamp} ===\n\n")
                if self.llm_config:
                    f.write(f"LLM配置: {json.dumps(self.llm_config, ensure_ascii=False, indent=2)}\n\n")
            
            logger.info(f"调试日志将写入: {self.debug_file}")
        except Exception as e:
            logger.error(f"初始化调试文件时出错: {str(e)}")
            self.debug_file = None
    
    def _write_debug(self, message: str) -> None:
        """
        写入调试信息到文件
        
        Args:
            message: 调试信息
        """
        if not self.debug_file:
            return
        
        try:
            with open(self.debug_file, "a", encoding="utf-8") as f:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            logger.error(f"写入调试信息时出错: {str(e)}")
    
    def set_llm(self, llm_name: str) -> bool:
        """
        设置使用的LLM
        
        Args:
            llm_name: LLM名称，对应配置文件中的alternatives键
            
        Returns:
            是否成功设置
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("langchain相关模块未安装，无法设置LLM")
            return False
            
        # 获取备选LLM配置
        alternatives = self.config.get("llm", {}).get("alternatives", {})
        llm_config = alternatives.get(llm_name)
        
        if not llm_config:
            logger.warning(f"未找到名为 {llm_name} 的LLM配置")
            return False
        
        provider = llm_config.get("provider", "").lower()
        model = llm_config.get("model", "")
        temperature = llm_config.get("temperature", 0.7)
        api_key = llm_config.get("api_key", "")
        api_base = llm_config.get("api_base", "")
        
        # 如果没有提供API密钥，尝试从环境变量获取
        if not api_key:
            if provider == "openai":
                api_key = os.environ.get("OPENAI_API_KEY", "")
            elif provider == "anthropic":
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        
        # 如果没有提供API基础URL，尝试从环境变量获取
        if not api_base:
            if provider == "openai":
                api_base = os.environ.get("OPENAI_API_BASE", "")
            elif provider == "anthropic":
                api_base = os.environ.get("ANTHROPIC_API_BASE", "")
            elif provider == "ollama":
                api_base = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
        
        # 构建LLM配置
        self.llm_config = {
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "api_key": api_key,
            "api_base": api_base
        }
        
        # 初始化Langchain LLM实例
        self._initialize_langchain_llm()
        
        # 保存当前提供商和模型信息
        self.provider = provider
        self.model = model
        
        logger.info(f"已切换LLM配置: {provider}/{model}")
        return True
    
    async def _safe_callback(
        self,
        callback: Optional[Callable[[str], Awaitable[None]]],
        content: str
    ) -> None:
        """
        安全地调用回调函数，如果回调函数为空则忽略

        Args:
            callback: 回调函数，可能为None
            content: 要发送的内容
        """
        if callback:
            await callback(content)

    async def call_llm(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        stream: bool = False,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """
        调用Langchain LLM接口

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            stream: 是否使用流式输出
            stream_callback: 流式输出回调函数，用于处理每个内容块

        Returns:
            LLM响应内容
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("langchain相关模块未安装，无法调用LLM")
            
        if not self.llm:
            raise ValueError("LLM实例未初始化")
            
        try:
            # 记录要发送给LLM的信息
            logger.info(f"发送给LLM的信息 - 模型: {self.provider}/{self.model}, 温度: {self.llm_config['temperature']}")
            logger.debug(f"系统提示词: {system_prompt}")
            logger.debug(f"用户提示词: {user_prompt}")
            
            # 写入调试文件
            self._write_debug(f"=== 发送给LLM的信息 ===")
            self._write_debug(f"模型: {self.provider}/{self.model}, 温度: {self.llm_config['temperature']}")
            self._write_debug(f"系统提示词:\n{system_prompt}")
            self._write_debug(f"用户提示词:\n{user_prompt}")
            
            # 构建消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # 创建提示模板
            prompt = ChatPromptTemplate.from_messages(messages)
            
            # 创建输出解析器
            output_parser = StrOutputParser()
            
            # 创建链
            chain = prompt | self.llm | output_parser
            
            # 调用LLM
            if stream:
                # 处理流式响应
                full_response = ""
                try:
                    # 使用ainvoke方法并传入stream=True参数
                    async for chunk in chain.astream({}, {"stream": True}):
                        full_response += chunk
                        # 使用安全回调方法
                        await self._safe_callback(stream_callback, chunk)
                except Exception as e:
                    logger.error(f"流式处理时出错: {str(e)}")
                    # 如果流式处理失败，尝试使用普通方式调用
                    content = await chain.ainvoke({})
                    full_response = content
                    await self._safe_callback(stream_callback, full_response)
                
                # 写入调试文件
                self._write_debug(f"=== LLM响应内容（流式） ===")
                self._write_debug(full_response)
                
                return full_response
            else:
                # 处理普通响应
                content = await chain.ainvoke({})
                logger.debug(f"LLM响应内容: {content}")
                
                # 写入调试文件
                self._write_debug(f"=== LLM响应内容 ===")
                self._write_debug(content)
                
                return content
                
        except Exception as e:
            error_msg = f"调用LLM时出错: {str(e)}"
            logger.error(error_msg)
            self._write_debug(f"=== 错误 ===")
            self._write_debug(error_msg)
            raise 