from langgraph.graph import Command
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import NEXT
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from typing import Callable, Awaitable
from langchain_core.messages import HumanMessage
def chatbot(name: str, task: str, llm: BaseChatModel, config: Config, callback: Callable[[str], Awaitable[None]]):

    async def chatbot_impl(state: BaseState) -> Command:
        print(f"Chatbot {name} is running")
        messages = state.messages
        response = llm.stream(messages)
        result =''
        for chunk in response:
            result += chunk.content
            if callback:
                await callback(chunk.content)
        return Command(goto=NEXT, update={"messages": [
            HumanMessage(content=result, name=name)
        ]})

    return chatbot_impl
