import asyncio
from app.models.langchain_analyzer.main import LangChainAnalyzerModel

async def test():
    # 初始化模型
    model = LangChainAnalyzerModel()
    print("模型初始化成功")
    
    # 测试消息处理
    result = await model.on_chat_messages([{'role': 'user', 'content': '你好，请帮我分析一下这段文本'}], None)
    print(f"处理结果: {result}")

if __name__ == "__main__":
    asyncio.run(test()) 