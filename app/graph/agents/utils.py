"""
智能体工具函数，用于构建提示词和处理响应。
"""

import logging
import re
from typing import Dict, Any, Tuple, List, Optional, Callable, Awaitable
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)



def build_task_prompt(
    task_config: Dict[str, Any],
    **kwargs
) -> str:
    """
    构建任务提示词。
    
    Args:
        task_config: 任务配置
        **kwargs: 用于格式化任务描述的参数
    
    Returns:
        任务提示词
    """
    description = task_config.get("description", "")
    
    # 使用提供的参数格式化任务描述
    try:
        task_prompt = description.format(**kwargs)
    except KeyError as e:
        logger.warning(f"格式化任务描述时缺少参数: {e}")
        task_prompt = description
    
    return task_prompt


def build_messages(
    agent_prompt: str,
    task_prompt: str,
    history: Optional[List[Dict[str, str]]] = None
) -> List[Dict[str, Any]]:
    """
    构建消息列表。
    
    Args:
        agent_prompt: 智能体提示词
        task_prompt: 任务提示词
        history: 历史消息列表
    
    Returns:
        消息列表
    """
    messages = [
        SystemMessage(content=agent_prompt),
        HumanMessage(content=task_prompt)
    ]
    
    # 添加历史消息
    if history:
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
    
    return messages


async def stream_callback(
    content: str,
    callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> None:
    """
    流式回调函数，用于向用户发送消息。
    
    Args:
        content: 消息内容
        callback: 回调函数
    """
    if callback:
        await callback(content)


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    从文本中提取JSON对象。
    
    Args:
        text: 包含JSON对象的文本
    
    Returns:
        提取的JSON对象，如果提取失败则返回空字典
    """
    import json
    
    # 尝试查找JSON对象
    json_pattern = r'```json\s*([\s\S]*?)\s*```|{[\s\S]*}'
    match = re.search(json_pattern, text)
    
    if match:
        json_str = match.group(1) if match.group(1) else match.group(0)
        
        # 清理JSON字符串
        json_str = json_str.strip()
        if not json_str.startswith('{'):
            json_str = '{' + json_str
        if not json_str.endswith('}'):
            json_str = json_str + '}'
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            return {}
    
    return {} 