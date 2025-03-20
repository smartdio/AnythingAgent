# LangGraph 多Agent图流程实现指南

## 1. 简介

LangGraph 是一个强大的工具，用于构建基于图的语言处理工作流。在多Agent系统中，LangGraph 提供了一种灵活的方式来组织和协调不同的智能体（Agent），使它们能够协同工作，解决复杂问题。本文档基于 `MultiAgentModel` 和 `LangChainAnalyzerModel` 的实现，详细介绍如何使用 LangGraph 构建多Agent图流程。

## 2. 多Agent系统架构

多Agent系统通常由以下几个部分组成：

1. **状态管理**：定义和管理系统状态，作为不同Agent之间共享信息的媒介
2. **Agent节点**：实现各种专门的智能体，每个智能体负责特定的任务
3. **工作流图**：定义Agent之间的交互和执行流程
4. **路由逻辑**：决定工作流的执行路径，控制哪个Agent在什么时候执行

## 3. 实现多Agent系统的步骤

### 3.1 定义状态类型

首先，需要定义一个状态类型，用于在不同Agent之间传递信息。通常使用 `TypedDict` 来定义状态类型：

```python
from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict):
    """多Agent状态类型"""
    messages: List[Dict[str, str]]  # 消息历史
    message: str                    # 当前消息
    thinking: bool                  # 是否在思考
    next: str                       # 下一个节点
```

### 3.2 定义配置类

配置类用于存储系统配置，包括LLM配置、任务配置、Agent配置等：

```python
class Config:
    """配置类"""
    llm: Any                        # 语言模型
    tasks: Dict[str, Any]           # 任务配置
    agents: Dict[str, Any]          # Agent配置
    config: Dict[str, Any]          # 原始配置
    callback: Optional[Callable]    # 回调函数
```

### 3.3 实现Agent节点

每个Agent节点是一个函数，接收状态作为输入，执行特定任务，然后返回更新后的状态。在多Agent系统中，通常使用工厂函数来创建Agent节点：

```python
def supervisor(config: Config):
    """主管Agent，负责协调其他Agent的工作"""
    llm = config.llm
    task = config.tasks["supervisor_task"]
    agent = config.agents["supervisor"]
    callback = config.callback
    
    # 获取所有可用的Agent
    members = [agent_name for agent_name in config.agents.keys() if agent_name != "supervisor"]
    options = members + ["FINISH"]
    
    # 构建提示词
    def _build_prompts(task, agent, user_message):
        # 构建Agent提示词和任务提示词
        # ...
        return agent_message, task_message
    
    # 定义路由类型
    class Router(TypedDict):
        """决定下一个执行的Agent"""
        next: str
    
    # 实现Agent逻辑
    async def supervisor_agent(state: GraphState) -> Command:
        # 构建提示词
        agent_message, task_message = _build_prompts(task, agent, state["message"])
        # 调用LLM获取决策
        response = await llm.with_structured_output(Router).ainvoke([agent_message, task_message])
        # 处理响应
        await callback(response["next"])
        goto = response["next"]
        if goto == "FINISH":
            goto = END
        # 返回命令，包括下一个节点和状态更新
        return Command(goto=goto, update={"next": goto})
    
    return supervisor_agent
```

类似地，可以实现其他专门的Agent，如研究员、编码员等：

```python
def researcher(config: Config):
    """研究员Agent，负责信息搜索和收集"""
    # ...
    
    async def researcher_agent(state: GraphState) -> Command:
        # 实现研究逻辑
        # ...
        # 返回结果并指定下一个节点
        return Command(
            update={"messages": [HumanMessage(content=result, name="researcher")]},
            goto="supervisor"
        )
    
    return researcher_agent

def coder(config: Config):
    """编码员Agent，负责编写和执行代码"""
    # ...
    
    async def coder_agent(state: GraphState) -> Command:
        # 实现编码逻辑
        # ...
        # 返回结果并指定下一个节点
        return Command(
            update={"messages": [HumanMessage(content=result, name="coder")]},
            goto="supervisor"
        )
    
    return coder_agent
```

### 3.4 构建工作流图

使用 LangGraph 的 `StateGraph` 构建工作流图，定义节点和边：

```python
def _init_workflow(self, config: Config) -> None:
    """初始化工作流"""
    try:
        # 创建状态图
        workflow = StateGraph(GraphState)
        
        # 添加节点
        workflow.add_node('supervisor', supervisor(config))
        workflow.add_node('researcher', researcher(config))
        workflow.add_node('coder', coder(config))
        
        # 添加边
        workflow.add_edge(START, 'supervisor')  # 从起点到主管
        
        # 编译工作流
        self.workflow = workflow.compile()
    except Exception as e:
        logger.error(f"初始化工作流失败: {e}")
        self.workflow = None
```

### 3.5 实现路由逻辑

在更复杂的系统中，可能需要单独的路由函数来决定工作流的执行路径：

```python
def analyzer_route(state: AnalyzerState):
    """分析器路由函数"""
    if "NEED_PLAN" in state["analysis_result"]:
        return "planner"  # 需要规划，转到规划器
    else:
        return "end"      # 不需要规划，结束

def worker_route(state: AnalyzerState):
    """工作器路由函数"""
    if state["tasks"] and len(state["tasks"]) > len(state["completed_tasks"]):
        return "executor"  # 还有任务未完成，继续执行
    else:
        return "end"       # 所有任务已完成，结束
```

然后在工作流中使用这些路由函数：

```python
# 添加条件边
workflow.add_conditional_edges("analyzer", analyzer_route, {"end": "feeback", "planner": "planner"})
workflow.add_conditional_edges("end_thinking", worker_route, {"end": END, "executor": "executor"})
workflow.add_conditional_edges("executor", worker_route, {"end": END, "executor": "executor"})
```

## 4. 执行工作流

在模型的 `on_chat_messages` 方法中执行工作流：

```python
async def on_chat_messages(self, messages, callback=None):
    # 初始化配置和工作流
    config = Config()
    config.llm = init_chat_model(...)
    config.tasks = self.cf["tasks"]
    config.agents = self.cf["agents"]
    config.callback = callback
    
    self._init_workflow(config)
    
    # 准备初始状态
    state = {
        "messages": messages,
        "message": messages[-1]["content"],
        "thinking": False,
        "next": ""
    }
    
    # 执行工作流
    try:
        async for event in self.workflow.astream(state):
            if callback and "message" in event:
                await callback(event["message"])
    except Exception as e:
        logger.error(f"执行工作流时出错: {str(e)}")
        return f"执行工作流时出错: {str(e)}"
```

## 5. 多Agent系统的两种实现方式

基于提供的代码示例，我们可以看到两种不同的多Agent系统实现方式：

### 5.1 基于Command的实现 (MultiAgentModel)

在 `MultiAgentModel` 中，每个Agent节点返回一个 `Command` 对象，包含两个关键信息：
- `goto`：指定下一个要执行的节点
- `update`：指定要更新的状态字段

这种方式允许Agent自己决定下一步执行哪个节点，实现了更灵活的控制流程。

```python
return Command(goto=goto, update={"next": goto})
```

### 5.2 基于条件边的实现 (LangChainAnalyzerModel)

在 `LangChainAnalyzerModel` 中，使用条件边和路由函数来决定下一个执行的节点：

```python
workflow.add_conditional_edges("analyzer", analyzer_route, {"end": "feeback", "planner": "planner"})
```

路由函数根据状态内容返回下一个节点的名称：

```python
def analyzer_route(state: AnalyzerState):
    if "NEED_PLAN" in state["analysis_result"]:
        return "planner"
    else:
        return "end"
```

这种方式将控制流程与Agent逻辑分离，使系统结构更清晰。

## 6. 最佳实践

### 6.1 状态设计

- 使用 `TypedDict` 明确定义状态结构
- 状态应包含所有必要的信息，但避免冗余数据
- 考虑状态的序列化和反序列化需求

### 6.2 Agent设计

- 每个Agent应专注于单一职责
- 使用工厂函数创建Agent节点，便于配置和复用
- 明确Agent之间的通信协议

### 6.3 工作流设计

- 使用条件边实现复杂的控制流程
- 考虑使用子图实现模块化设计
- 确保工作流有明确的终止条件

### 6.4 错误处理

- 在Agent节点中捕获和处理异常
- 记录详细的错误信息
- 考虑添加专门的错误处理节点

## 7. 示例：简单的多Agent系统

下面是一个简化的多Agent系统示例，包含一个主管Agent和两个专家Agent：

```python
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END, START
from langgraph.types import Command

# 定义状态类型
class SimpleState(TypedDict):
    query: str
    result: str
    next: str

# 定义Agent节点
def manager(llm):
    async def manager_agent(state: SimpleState) -> Command:
        query = state["query"]
        if "research" in query.lower():
            return Command(goto="researcher", update={"next": "researcher"})
        elif "code" in query.lower():
            return Command(goto="coder", update={"next": "coder"})
        else:
            return Command(goto=END, update={"result": "I can't help with that."})
    return manager_agent

def researcher(llm):
    async def researcher_agent(state: SimpleState) -> Command:
        query = state["query"]
        result = f"Research result for: {query}"
        return Command(goto=END, update={"result": result})
    return researcher_agent

def coder(llm):
    async def coder_agent(state: SimpleState) -> Command:
        query = state["query"]
        result = f"Code result for: {query}"
        return Command(goto=END, update={"result": result})
    return coder_agent

# 构建工作流
workflow = StateGraph(SimpleState)
workflow.add_node("manager", manager(llm))
workflow.add_node("researcher", researcher(llm))
workflow.add_node("coder", coder(llm))
workflow.add_edge(START, "manager")
compiled_workflow = workflow.compile()

# 执行工作流
result = await compiled_workflow.ainvoke({"query": "Please research about climate change", "result": "", "next": ""})
print(result["result"])
```

## 8. 总结

使用 LangGraph 实现多Agent系统的关键步骤包括：

1. 定义状态类型和配置类
2. 实现各种专门的Agent节点
3. 构建工作流图，定义节点和边
4. 实现路由逻辑，控制工作流执行路径
5. 在模型中执行工作流

LangGraph 提供了灵活的方式来组织和协调不同的Agent，使它们能够协同工作，解决复杂问题。通过合理设计状态、Agent和工作流，可以构建出功能强大、可维护的多Agent系统。

## 参考资料

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 文档](https://python.langchain.com/docs/get_started/introduction) 