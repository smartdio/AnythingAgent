"""
智能体工具函数，用于构建提示词和处理响应。
"""

import logging
import re
from typing import Dict, Any, Tuple, List, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


def SystemMessage(content: str, name: str = "system") :
    return {"role": "system", "content": content, "name": name}

def HumanMessage(content: str, name: str = "user") :
    return {"role": "user", "content": content, "name": name}

def AIMessage(content: str, name: str = "assistant") :
    return {"role": "assistant", "content": content, "name": name}


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