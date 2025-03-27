from langgraph.types import Command
from langchain_core.language_models.chat_models import BaseChatModel
from app.graph.states.base_state import BaseState
from typing import Callable, Awaitable
from app.graph.agents.utils import HumanMessage, SystemMessage, AIMessage, extract_messages
from typing import Dict
def chatbot(name: str, agent:Dict[str,str], task: Dict[str,str], llm: BaseChatModel, callback: Callable[[str], Awaitable[None]]):

    async def chatbot_impl(state: BaseState) -> Command:
        print(f"Chatbot {name} is running")
        messages = state['messages']
        history, last_user_message, last_system_message = extract_messages(messages)
        agent_description = agent.get('description')
        sys_prompt = agent_description.format(message=last_user_message, prompt=last_system_message)
        system_message = SystemMessage(content=sys_prompt, name=name)
        task_description = task.get('description')
        task_prompt = task_description.format(message=last_user_message, prompt=last_system_message, history=history)
        human_message = HumanMessage(content=task_prompt, name=name)
        result = ""
        async for chunk in llm.astream([system_message, human_message]):
            result += chunk.content
            if callback:
                await callback(chunk.content)
        # print(f"chatbot result: {result} \n")
        messages.append(AIMessage(content=result, name=name))
        return Command(update={"messages": messages})

    return chatbot_impl
