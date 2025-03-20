from typing import List, Dict, Any, Optional, Callable, Awaitable
import logging
from pathlib import Path

from app.models.base import AnythingBaseModel
from app.models.llm_manager import LiteLLMManager

logger = logging.getLogger(__name__)

class ExampleModel(AnythingBaseModel):
    """
    示例模型类，展示如何通过组合方式使用 LiteLLMManager
    """
    
    def __init__(self):
        super().__init__()
        
        # 通过组合方式使用 LiteLLMManager
        self.llm_manager = LiteLLMManager(
            model_dir=self.model_dir,
            config=self.config
        )
        
        # 初始化模型特定的属性
        self.history = []
    
    async def on_chat_messages(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        """
        处理聊天消息
        
        Args:
            messages: 消息列表，每个消息是包含角色和内容的字典
            callback: 用于流式输出的异步回调函数
            
        Returns:
            如果是非流式模式（callback=None），返回完整的响应字符串
            如果是流式模式（callback不为None），通过回调发送内容，返回None
        """
        try:
            # 记录消息历史
            self.history.extend(messages)
            
            # 提取最后一条用户消息
            user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
            
            if not user_message:
                return "未找到用户消息"
            
            # 构建系统提示词
            system_prompt = "你是一个有用的AI助手。"
            
            # 使用 LiteLLMManager 调用 LLM
            if callback:
                # 流式模式
                await self.llm_manager.call_llm(
                    system_prompt=system_prompt,
                    user_prompt=user_message,
                    stream=True,
                    stream_callback=callback
                )
                return None
            else:
                # 非流式模式
                response = await self.llm_manager.call_llm(
                    system_prompt=system_prompt,
                    user_prompt=user_message,
                    stream=False
                )
                return response
                
        except Exception as e:
            error_msg = f"处理聊天消息时出错: {str(e)}"
            logger.error(error_msg)
            self._write_debug(f"=== 错误 ===\n{error_msg}")
            return f"发生错误: {str(e)}"
    
    async def on_chat_start(self) -> None:
        """
        聊天开始时的钩子方法
        """
        self.history = []
        self._write_debug("=== 聊天开始 ===")
    
    async def on_chat_end(self) -> None:
        """
        聊天结束时的钩子方法
        """
        self._write_debug("=== 聊天结束 ===")
    
    def set_llm(self, llm_name: str) -> bool:
        """
        设置使用的LLM
        
        Args:
            llm_name: LLM名称
            
        Returns:
            是否成功设置
        """
        return self.llm_manager.set_llm(llm_name) 