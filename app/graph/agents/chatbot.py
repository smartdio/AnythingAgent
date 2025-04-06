from langgraph.types import Command
from langchain_core.language_models.chat_models import BaseChatModel
from app.graph.states.base_state import BaseState
from typing import Callable, Awaitable
from app.graph.agents.utils import HumanMessage, SystemMessage, AIMessage, extract_messages
from typing import Dict
def chatbot(name: str, agent:Dict[str,str], task: Dict[str,str], llm: BaseChatModel, callback: Callable[[str], Awaitable[None]]):

    async def chatbot_impl(state: BaseState) -> Command:

        prompt = agent.get("description")
        system_message = SystemMessage(content=prompt, name=name)
        messages = state["messages"]
        new_messages = [system_message] + messages
        result = ""
        async for chunk in llm.astream(new_messages):
            result += chunk.content
            if callback:
                await callback(chunk.content)
        print(f"chatbot result: {result} \n")
        messages.append(AIMessage(content=result, name=name))
        return Command(update={"messages": messages})

    return chatbot_impl
