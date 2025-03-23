"""
基础状态类型定义，作为所有其他状态类型的基础。
"""

from typing import TypedDict, List, Dict, Any, Optional


class BaseState(TypedDict):
    """
    基础状态类型，所有其他状态类型的基础。
    
    属性:
        messages: 消息历史，包含用户和系统的消息记录
        message: 当前消息，通常是最新的用户输入
        thinking: 是否在思考中，用于控制思考状态的显示
        next: 下一个节点的名称，用于路由控制
    """
    config: Dict[str, Any]          # 配置信息
    messages: List[Dict[str, str]]  # 消息历史
    message: str                    # 当前消息, 用户输入的消息
    prompt: str                     # 系统提示, 系统提示词
    thinking: bool                  # 是否在思考
    next: str                       # 下一个节点 
    tasks: List[Dict[str, Any]]     # 任务列表
    # 任务字典结构示例:
    # {
    #     "id": str,              # 任务唯一标识符
    #     "title": str,           # 任务标题
    #     "prompt": str,     # 任务详细描述
    # }
    completed_tasks: List[Dict[str, Any]] # 已完成任务列表
    members: List[Dict[str, Any]]    # 成员列表
    # 成员字典结构示例:
    # {
    #     "name": str,           # 成员名称
    #     "role": str,   # 成员描述
    #     "goal": str,           # 成员目标
    # }



