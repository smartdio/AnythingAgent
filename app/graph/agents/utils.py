"""
智能体工具函数，用于构建提示词和处理响应。
"""

import logging
import re
from typing import Dict, Any, Tuple, List, Optional, Callable, Awaitable, Union
from app.schemas.chat import Message
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


def convert_to_langchain_messages(messages: List[Message]) -> List[Any]:
    """
    将app.schemas.chat中的Message列表转换为langchain中的Message列表。
    
    此函数支持以下转换:
    - 系统消息 -> langchain_core.messages.SystemMessage
    - 用户消息 -> langchain_core.messages.HumanMessage  
    - 助手消息 -> langchain_core.messages.AIMessage
    - 工具消息 -> langchain_core.messages.ToolMessage (如果角色为"tool")
    
    同时支持多模态内容转换:
    - TextContent -> {"type": "text", "text": ...}
    - ImageContent -> {"type": "image_url", "image_url": {"url": ...}}
    
    Args:
        messages: app.schemas.chat.Message对象列表
        
    Returns:
        langchain_core.messages中相应Message对象列表
    """
    from langchain_core.messages import (
        AIMessage as LCAIMessage,
        HumanMessage as LCHumanMessage,
        SystemMessage as LCSystemMessage,
        ToolMessage as LCToolMessage
    )
    
    langchain_messages = []
    
    for msg in messages:
        content = msg.content
        name = msg.name
        
        # 处理多模态内容（将我们的格式转换为langchain支持的格式）
        if isinstance(content, list):
            # 将我们的TextContent和ImageContent对象转换为langchain支持的格式
            lc_content = []
            for item in content:
                if item.type == "text":
                    lc_content.append({"type": "text", "text": item.text})
                elif item.type == "image":
                    lc_content.append({
                        "type": "image_url",
                        "image_url": {"url": item.image_url.url}
                    })
            content = lc_content
        
        # 根据角色创建不同类型的消息
        if msg.role == "system":
            langchain_messages.append(LCSystemMessage(content=content, name=name))
        elif msg.role == "user":
            langchain_messages.append(LCHumanMessage(content=content, name=name))
        elif msg.role == "assistant":
            langchain_messages.append(LCAIMessage(content=content, name=name))
        elif msg.role == "tool":
            # 对于工具消息，我们需要工具调用ID，默认为空字符串
            # 如果需要支持真实的工具调用ID，可能需要在Message模型中添加相应字段
            langchain_messages.append(LCToolMessage(content=content, tool_call_id="", name=name))
        else:
            # 对于未知角色，默认使用HumanMessage
            logger.warning(f"未知消息角色: {msg.role}，将其视为用户消息")
            langchain_messages.append(LCHumanMessage(content=content, name=name or msg.role))
    
    return langchain_messages


def extract_messages(messages: List[Message], limit: int = 30000) -> Tuple[str, str, str]:
    """
    从消息列表中提取关键消息并合并历史记录。
    1. 提取最后一条系统提示词
    2. 提取最后一条用户消息
    3. 合并其余历史消息（不超过字数限制）
    
    Args:
        messages: 消息历史记录列表，每条消息包含 role, content, name
        limit: 合并后文本的最大字数限制，默认30000字
        
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
        content = msg.get('content', '')
        # 确保 content 是字符串
        if isinstance(content, (list, tuple)):
            content = ' '.join(str(item) for item in content)
        elif not isinstance(content, str):
            content = str(content)
            
        if msg["role"] == "user" and not last_user_message:
            last_user_message = content
        elif msg["role"] == "system" and not last_system_message:
            last_system_message = content
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
        content = msg.get('content', '')
        
        # 确保 content 是字符串
        if isinstance(content, (list, tuple)):
            content = ' '.join(str(item) for item in content)
        elif not isinstance(content, str):
            content = str(content)
            
        formatted_msg = f"[{role_name}]: {content}\n"
        
        # 检查添加这条消息是否会超过限制
        if current_length + len(formatted_msg) > limit:
            logger.debug(f"历史消息长度将超过限制: {current_length} + {len(formatted_msg)} > {limit}")
            break
            
        history.insert(0, formatted_msg)  # 在开头插入消息，保持时间顺序
        current_length += len(formatted_msg)
    
    # 确保返回的都是字符串类型
    return ("".join(history),
            str(last_user_message).strip(),
            str(last_system_message).strip()) 