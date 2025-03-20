# 图流程组件设计文档

## 1. 概述

我们将在 `app/graph` 包中实现一系列可复用的组件，用于构建基于 LangGraph 的多 Agent 图流程系统。这些组件将包括常用的节点（Node）、智能体（Agent）、图（Graph）和状态（State）定义，以便于快速构建和部署多 Agent 系统。

## 2. 目录结构设计

```
app/graph/
├── __init__.py
├── agents/             # 预定义的智能体
│   ├── __init__.py
│   ├── supervisor.py   # 主管智能体
│   ├── researcher.py   # 研究员智能体
│   ├── coder.py        # 编码员智能体
│   └── analyst.py      # 分析员智能体
├── nodes/              # 预定义的节点
│   ├── __init__.py
│   ├── thinking.py     # 思考节点
│   ├── planning.py     # 规划节点
│   ├── execution.py    # 执行节点
│   └── feedback.py     # 反馈节点
├── routes/             # 路由函数
│   ├── __init__.py
│   ├── basic_routes.py # 基础路由函数
│   └── advanced_routes.py # 高级路由函数
├── states/             # 状态定义
│   ├── __init__.py
│   ├── base_state.py   # 基础状态类型
│   └── config.py       # 配置类
└── graphs/             # 预定义的图
    ├── __init__.py
    ├── sequential.py   # 顺序执行图
    ├── branching.py    # 分支执行图
    └── team.py         # 团队协作图
```

## 3. 组件设计

### 3.1 状态（States）

#### 3.1.1 基础状态类型（BaseState）

```python
from typing import TypedDict, List, Dict, Any, Optional

class BaseState(TypedDict):
    """基础状态类型，所有其他状态类型的基础"""
    messages: List[Dict[str, str]]  # 消息历史
    message: str                    # 当前消息
    thinking: bool                  # 是否在思考
    next: str                       # 下一个节点
```

#### 3.1.2 配置类（Config）

```python
from typing import Dict, Any, Optional, Callable, Awaitable
from langchain_core.language_models.chat_models import BaseChatModel

class Config:
    """配置类，用于存储系统配置"""
    llm: BaseChatModel              # 语言模型
    tasks: Dict[str, Any]           # 任务配置
    agents: Dict[str, Any]          # Agent配置
    config: Dict[str, Any]          # 原始配置
    callback: Optional[Callable[[str], Awaitable[None]]]  # 回调函数
```

### 3.2 节点（Nodes）

#### 3.2.1 思考节点（ThinkingNode）

```python
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from typing import Callable, Awaitable

def start_thinking_node(config: Config) -> Callable[[BaseState], Awaitable[BaseState]]:
    """创建开始思考节点"""
    async def start_thinking_node_impl(state: BaseState) -> BaseState:
        await config.callback("<think>\n ...")
        state["thinking"] = True
        return state
    return start_thinking_node_impl

def end_thinking_node(config: Config) -> Callable[[BaseState], Awaitable[BaseState]]:
    """创建结束思考节点"""
    async def end_thinking_node_impl(state: BaseState) -> BaseState:
        await config.callback("</think>")
        state["thinking"] = False
        return state
    return end_thinking_node_impl
```

#### 3.2.2 规划节点（PlanningNode）

```python
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from typing import Callable, Awaitable

def planning_node(config: Config) -> Callable[[BaseState], Awaitable[BaseState]]:
    """创建规划节点"""
    async def planning_node_impl(state: BaseState) -> BaseState:
        # 实现规划逻辑
        # ...
        return state
    return planning_node_impl
```

### 3.3 智能体（Agents）

#### 3.3.1 主管智能体（SupervisorAgent）

```python
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from typing import Dict, Any, TypedDict
from langgraph.types import Command
from langgraph.graph import END

def supervisor_agent(config: Config):
    """创建主管智能体"""
    llm = config.llm
    task = config.tasks["supervisor_task"]
    agent = config.agents["supervisor"]
    callback = config.callback
    
    # 获取所有可用的Agent
    members = [agent_name for agent_name in config.agents.keys() if agent_name != "supervisor"]
    options = members + ["FINISH"]
    
    # 定义路由类型
    class Router(TypedDict):
        """决定下一个执行的Agent"""
        next: str
    
    # 实现Agent逻辑
    async def supervisor_impl(state: BaseState) -> Command:
        # 构建提示词
        # 调用LLM获取决策
        # 处理响应
        # 返回命令
        return Command(goto=goto, update={"next": goto})
    
    return supervisor_impl
```

#### 3.3.2 研究员智能体（ResearcherAgent）

```python
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from typing import Dict, Any
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent
from langchain_community.tools.tavily_search import TavilySearchResults

def researcher_agent(config: Config):
    """创建研究员智能体"""
    llm = config.llm
    callback = config.callback
    
    # 设置搜索工具
    tavily_tool = TavilySearchResults(max_results=5)
    
    # 创建ReAct Agent
    _research_agent = create_react_agent(llm, tools=[tavily_tool])
    
    async def researcher_impl(state: BaseState) -> Command:
        # 实现研究逻辑
        # 返回结果
        return Command(update=update, goto="supervisor")
    
    return researcher_impl
```

### 3.4 路由函数（Routes）

#### 3.4.1 基础路由函数

```python
from app.graph.states.base_state import BaseState

def analyzer_route(state: BaseState):
    """分析器路由函数"""
    if "NEED_PLAN" in state.get("analysis_result", ""):
        return "planner"
    else:
        return "end"

def worker_route(state: BaseState):
    """工作器路由函数"""
    if state.get("tasks", []) and len(state.get("tasks", [])) > len(state.get("completed_tasks", [])):
        return "executor"
    else:
        return "end"
```

### 3.5 图（Graphs）

#### 3.5.1 顺序执行图（SequentialGraph）

```python
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from app.graph.nodes.thinking import start_thinking_node, end_thinking_node
from app.graph.nodes.planning import planning_node
from app.graph.nodes.execution import execution_node
from app.graph.nodes.feedback import feedback_node
from langgraph.graph import StateGraph, END, START

def create_sequential_graph(config: Config):
    """创建顺序执行图"""
    # 创建状态图
    workflow = StateGraph(BaseState)
    
    # 添加节点
    workflow.add_node("start_thinking", start_thinking_node(config))
    workflow.add_node("planning", planning_node(config))
    workflow.add_node("execution", execution_node(config))
    workflow.add_node("feedback", feedback_node(config))
    workflow.add_node("end_thinking", end_thinking_node(config))
    
    # 添加边
    workflow.add_edge("start_thinking", "planning")
    workflow.add_edge("planning", "execution")
    workflow.add_edge("execution", "feedback")
    workflow.add_edge("feedback", "end_thinking")
    workflow.add_edge("end_thinking", END)
    
    # 设置入口点
    workflow.set_entry_point("start_thinking")
    
    # 编译工作流
    return workflow.compile()
```

#### 3.5.2 团队协作图（TeamGraph）

```python
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from app.graph.agents.supervisor import supervisor_agent
from app.graph.agents.researcher import researcher_agent
from app.graph.agents.coder import coder_agent
from app.graph.agents.analyst import analyst_agent
from langgraph.graph import StateGraph, END, START

def create_team_graph(config: Config):
    """创建团队协作图"""
    # 创建状态图
    workflow = StateGraph(BaseState)
    
    # 添加节点
    workflow.add_node("supervisor", supervisor_agent(config))
    workflow.add_node("researcher", researcher_agent(config))
    workflow.add_node("coder", coder_agent(config))
    workflow.add_node("analyst", analyst_agent(config))
    
    # 添加边
    workflow.add_edge(START, "supervisor")
    
    # 编译工作流
    return workflow.compile()
```

## 4. 使用示例

### 4.1 创建和使用顺序执行图

```python
from app.graph.states.config import Config
from app.graph.graphs.sequential import create_sequential_graph
from langchain.chat_models import init_chat_model

# 初始化配置
config = Config()
config.llm = init_chat_model(model="openai:gpt-4")
config.tasks = {...}  # 任务配置
config.agents = {...}  # Agent配置
config.callback = async_callback_function

# 创建工作流
workflow = create_sequential_graph(config)

# 准备初始状态
state = {
    "messages": [...],
    "message": "用户消息",
    "thinking": False,
    "next": ""
}

# 执行工作流
result = await workflow.ainvoke(state)
```

### 4.2 创建和使用团队协作图

```python
from app.graph.states.config import Config
from app.graph.graphs.team import create_team_graph
from langchain.chat_models import init_chat_model

# 初始化配置
config = Config()
config.llm = init_chat_model(model="openai:gpt-4")
config.tasks = {
    "supervisor_task": {...},
    "research_task": {...},
    "coding_task": {...}
}
config.agents = {
    "supervisor": {...},
    "researcher": {...},
    "coder": {...}
}
config.callback = async_callback_function

# 创建工作流
workflow = create_team_graph(config)

# 准备初始状态
state = {
    "messages": [...],
    "message": "用户消息",
    "thinking": False,
    "next": ""
}

# 执行工作流
async for event in workflow.astream(state):
    if "message" in event:
        print(event["message"])
```

## 5. 扩展性设计

该组件库设计为高度可扩展的，用户可以：

1. **自定义新的状态类型**：继承 `BaseState` 添加新的字段
2. **自定义新的节点**：按照节点工厂函数模式创建新的节点
3. **自定义新的智能体**：实现新的智能体工厂函数
4. **自定义新的图**：组合现有节点和智能体，或添加新的节点和智能体

## 6. 后续开发计划

1. **添加更多预定义智能体**：如数据分析师、创意写手等
2. **添加更多工具集成**：如数据库访问、API调用等
3. **添加监控和调试功能**：可视化工作流执行过程
4. **添加性能优化功能**：缓存、并行执行等
5. **添加更多图模板**：适用于不同场景的预定义图

## 7. 总结

通过在 `app/graph` 包中实现这些可复用组件，我们可以大大简化多Agent系统的开发过程，提高开发效率和代码质量。这些组件将为构建复杂的多Agent系统提供坚实的基础，同时保持足够的灵活性，以适应各种不同的应用场景。 