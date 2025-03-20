from typing import TypedDict, List, Dict, Any, Optional, Callable, Awaitable

# 定义状态类型
class AnalyzerState(TypedDict):
    """分析器状态类型"""
    history_context: str  # 格式化的历史上下文
    user_message: str  # 当前用户消息
    system_message: str  # 系统消息
    analysis_result: Optional[str]  # 分析结果
    tasks: List[Dict[str, str]]  # 任务列表
    completed_tasks: List[Dict[str, str]]  # 已完成任务
    final_result: Optional[str]  # 最终结果
    execution_results: List[str]  # 执行结果
    stream_result: str  # 流式结果
    message: str  # 消息
    thinking: bool  # 是否在思考

class AnalyzerConfig():
    llm: Dict[str, Any]  # LLM配置
    tasks: Dict[str, Any]  # 任务模板
    agents: Dict[str, Any]  # Agent配置
    config: Dict[str, Any]  # 配置信息
    callback: Callable[[AnalyzerState], Awaitable[None]]  # 回调函数
