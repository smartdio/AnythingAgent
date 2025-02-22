from typing import List, Dict, AsyncGenerator, Optional, Callable, Awaitable
import asyncio
import platform
import sys
import os
from app.models.base import AnythingBaseModel

class IsolatedTestModel(AnythingBaseModel):
    """
    在隔离环境中运行的测试模型。
    用于演示隔离环境的功能。
    """
    
    async def on_chat_messages(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        """处理聊天消息，支持流式输出"""
        # 获取环境信息
        env_info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": os.getcwd(),
            "env_vars": dict(os.environ)
        }
        
        # 获取最后一条用户消息
        last_message = None
        for msg in reversed(messages):
            if msg["role"] == "user":
                last_message = msg["content"]
                break
        
        responses = []
        
        # 生成响应
        responses.append("正在隔离环境中处理您的请求...\n")
        responses.append(f"收到消息：{last_message}\n")
        responses.append("\n环境信息：\n")
        
        # 逐行输出环境信息
        for key, value in env_info.items():
            if callback:
                await asyncio.sleep(0.5)  # 模拟处理延迟
            responses.append(f"{key}: {value}\n")
        
        # 测试第三方库
        try:
            import numpy as np
            responses.append("\n成功导入 numpy！\n")
            responses.append(f"numpy 版本: {np.__version__}\n")
        except ImportError:
            responses.append("\n未安装 numpy\n")
        
        responses.append("\n处理完成！")
        
        # 根据是否有callback决定返回方式
        if callback:
            for response in responses:
                await callback(response)
            return None
        else:
            return "".join(responses) 