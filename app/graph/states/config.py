"""
配置类定义，用于存储系统配置并支持从YAML文件加载。
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, Callable, Awaitable, Union, List
from pathlib import Path
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


class Config:
    """
    配置类，用于存储系统配置。
    
    属性:
        tasks: 任务配置字典
        agents: Agent配置字典
        config: 原始配置字典
        callback: 回调函数，用于流式输出
    """
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        初始化配置类。
        
        Args:
            config_path: 配置文件路径，如果不指定则使用当前目录下的 config.yaml
        """
        self.tasks: Dict[str, Any] = {}
        self.agents: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}
        
        # 如果没有指定配置文件路径，使用当前目录下的 config.yaml
        if config_path is None:
            config_path = Path.cwd() / "config.yaml"
        else:
            config_path = Path(config_path) if isinstance(config_path, str) else config_path
        
        self._load_config(config_path)
    
    def _load_config(self, config_path: Path) -> None:
        """
        从配置文件加载配置。
        
        Args:
            config_path: 配置文件路径
        """
        try:
            if not config_path.exists():
                logger.warning(f"配置文件不存在: {config_path}")
                return
            
            with open(config_path, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)
            
            if not config_dict:
                logger.warning(f"配置文件为空或格式错误: {config_path}")
                return
            
            self.update_from_dict(config_dict)
            logger.info(f"成功加载配置文件: {config_path}")
        
        except Exception as e:
            logger.error(f"加载配置文件时出错: {str(e)}")
    
    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        从字典更新配置。
        
        Args:
            config_dict: 配置字典
        """
        self.config.update(config_dict)
        
        # 更新任务配置
        if "tasks" in config_dict:
            self.tasks.update(config_dict["tasks"])
        
        # 更新Agent配置
        if "agents" in config_dict:
            self.agents.update(config_dict["agents"])
    
    def __repr__(self) -> str:
        """返回配置的字符串表示。"""
        return f"Config(tasks={list(self.tasks.keys())}, agents={list(self.agents.keys())})"


class ConfigLoader:
    """
    配置加载器，用于从YAML文件加载配置。
    
    属性:
        config_path: 配置文件路径
        config: 配置实例
    """
    def __init__(self, config_path: Union[str, Path]):
        """
        初始化配置加载器。
        
        Args:
            config_path: 配置文件路径，可以是字符串或Path对象
        """
        self.config_path = Path(config_path) if isinstance(config_path, str) else config_path
        self.config = Config()
        self._load_config()
    
    def _load_config(self) -> None:
        """从配置文件加载配置。"""
        try:
            if not self.config_path.exists():
                logger.warning(f"配置文件不存在: {self.config_path}")
                return
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)
            
            if not config_dict:
                logger.warning(f"配置文件为空或格式错误: {self.config_path}")
                return
            
            self.config.update_from_dict(config_dict)
            logger.info(f"成功加载配置文件: {self.config_path}")
        
        except Exception as e:
            logger.error(f"加载配置文件时出错: {str(e)}")
    
    def reload(self) -> None:
        """重新加载配置文件。"""
        logger.info(f"重新加载配置文件: {self.config_path}")
        self._load_config()
    
    def get_config(self) -> Config:
        """获取配置实例。"""
        return self.config
    
    @classmethod
    def from_default_locations(cls, config_name: str = "config.yaml") -> "ConfigLoader":
        """
        从默认位置加载配置文件。
        
        搜索顺序:
        1. 当前工作目录
        2. 用户主目录下的.config/app_name目录
        3. /etc/app_name目录
        
        Args:
            config_name: 配置文件名称
        
        Returns:
            ConfigLoader实例
        """
        # 应用名称，用于配置目录
        app_name = "anything_agent"
        
        # 可能的配置文件位置
        possible_locations = [
            Path.cwd() / config_name,
            Path.cwd() / "config" / config_name,
            Path.home() / ".config" / app_name / config_name,
            Path("/etc") / app_name / config_name
        ]
        
        # 查找第一个存在的配置文件
        for location in possible_locations:
            if location.exists():
                logger.info(f"从默认位置加载配置文件: {location}")
                return cls(location)
        
        # 如果没有找到配置文件，使用当前工作目录
        logger.warning(f"未找到配置文件，将使用当前工作目录: {possible_locations[0]}")
        return cls(possible_locations[0])


def load_config_from_yaml(config_path: Union[str, Path]) -> Dict[str, Any]:
    """
    从YAML文件加载配置。
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置字典
    """
    try:
        config_path = Path(config_path) if isinstance(config_path, str) else config_path
        
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_path}")
            return {}
        
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
        
        if not config_dict:
            logger.warning(f"配置文件为空或格式错误: {config_path}")
            return {}
        
        return config_dict
    
    except Exception as e:
        logger.error(f"加载配置文件时出错: {str(e)}")
        return {} 