from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple
import logging
import os
from logging.handlers import RotatingFileHandler
from app.models.langchain_factory import LangChainLLMFactory

# 配置日志记录器
def setup_logger():
    """配置日志记录器，添加日志轮转功能"""
    log_dir = Path(__file__).parent
    log_file = log_dir / "debug.log"
    
    # 创建日志记录器
    debug_logger = logging.getLogger("langchain_analyzer_debug")
    debug_logger.setLevel(logging.DEBUG)
    
    # 防止日志重复
    if not debug_logger.handlers:
        # 创建轮转文件处理器，最大文件大小为2MB，保留5个备份文件
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=2 * 1024 * 1024,  # 2MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 创建格式化器
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        
        # 添加处理器到日志记录器
        debug_logger.addHandler(file_handler)
    
    return debug_logger

# 初始化日志记录器
debug_logger = setup_logger()
logger = logging.getLogger(__name__)

def write_debug(content: str) -> None:
    """
    记录调试信息到日志文件，使用标准logging模块和日志轮转机制
    
    Args:
        content: 要记录的调试内容
    """
    try:
        # 使用专用的调试日志记录器记录信息
        debug_logger.debug(content)
    except Exception as e:
        logger.error(f"写入调试信息时出错: {str(e)}")

def init_llm(llm_config: Dict[str, Any]) -> Any:
    """初始化LLM"""
    llm = LangChainLLMFactory.create_llm(
        provider=llm_config.get("provider", "openai"),
        model=llm_config.get("model", "gpt-3.5-turbo"),
        temperature=llm_config.get("temperature", 0.7),
        api_key=llm_config.get("api_key", ""),
        api_base=llm_config.get("api_base", "")
    )
    return llm

def extract_think_tags(text: str) -> Tuple[str, str]:
    """
    Extract content within <think></think> tags from text.
    
    Args:
        text: The input text that may contain <think></think> tags
        
    Returns:
        tuple: (cleaned_text, think_content)
            - cleaned_text: The original text with <think></think> tags and their content removed
            - think_content: The content extracted from within the <think></think> tags
    """
    import re
    
    # Find all content within <think></think> tags
    think_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
    think_matches = think_pattern.findall(text)
    
    # Extract all think content
    think_content = "\n".join(think_matches) if think_matches else ""
    
    # Remove all <think></think> tags and their content from the original text
    cleaned_text = think_pattern.sub('', text)
    
    return cleaned_text, think_content
