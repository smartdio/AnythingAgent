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

def extract_messages(messages: List[Dict[str, str]], limit: int = 30000) -> Tuple[str, str, str]:
    """
    从消息列表中提取关键消息并合并历史记录。
    1. 提取最后一条系统提示词
    2. 提取最后一条用户消息
    3. 合并其余历史消息（不超过字数限制）
    
    Args:
        messages: 消息历史记录列表，每条消息包含 role, content, name
        limit: 合并后文本的最大字数限制，默认20000字
        
    Returns:
        Tuple[str, str, str]: (
            合并后的历史消息文本,
            最后一条用户消息,
            最后一条系统提示词
        )
    """
    if not messages:
        return "", "", ""
        
    history = []
    current_length = 0
    last_user_message = ""
    last_system_message = ""
    
    # 先找到最后一条用户消息和系统消息
    for msg in reversed(messages):
        if msg["role"] == "user" and not last_user_message:
            last_user_message = msg['content']
        elif msg["role"] == "system" and not last_system_message:
            last_system_message = msg['content']
        if last_user_message and last_system_message:
            break
    
    # 从最后一条消息开始处理历史消息（跳过最后一条用户消息）
    found_last_user = False
    for msg in reversed(messages):
        # 跳过 system 消息
        if msg["role"] == "system":
            continue
            
        # 如果是最后一条用户消息，标记并跳过
        if not found_last_user and msg["role"] == "user":
            found_last_user = True
            continue
            
        # 构建当前消息的格式化文本
        role_name = msg.get("name", msg["role"])
        formatted_msg = f"[{role_name}]: {msg['content']}\n"
        
        # 检查添加这条消息是否会超过限制
        if current_length + len(formatted_msg) > limit:
            print(f"history length: {current_length} + {len(formatted_msg)} > {limit}")
            break
            
        history.insert(0, formatted_msg)  # 在开头插入消息，保持时间顺序
        current_length += len(formatted_msg)
    
    return "".join(history), last_user_message.strip(), last_system_message.strip() 