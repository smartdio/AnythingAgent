# LangGraph 使用指南

## 1. 简介

LangGraph 是一个用于构建基于图的语言处理工作流的库，它是 LangChain 生态系统的一部分。LangGraph 允许开发者将复杂的语言处理任务分解为多个节点，并通过有向图的方式连接这些节点，形成一个完整的工作流。

LangGraph 的核心优势在于：
- 支持状态管理和共享
- 支持条件分支和循环
- 支持异步操作
- 与 LangChain 生态系统无缝集成

## 2. 核心概念

### 2.1 状态 (State)

在 LangGraph 中，状态是一个共享的数据结构，用于在图的不同节点之间传递信息。状态通常使用 `TypedDict` 或 Pydantic 模型定义，包含工作流所需的所有数据。

```python
from typing import TypedDict, List, Dict, Optional, Annotated

class MyState(TypedDict):
    messages: List[Dict[str, str]]  # 消息历史
    user_input: str                 # 用户输入
    result: Optional[str]           # 处理结果
```

### 2.2 节点 (Node)

节点是工作流中的处理单元，通常是一个函数，接收当前状态作为输入，执行某些操作，然后返回更新后的状态。

```python
async def process_node(state: MyState) -> dict:
    """处理用户输入的节点"""
    user_input = state["user_input"]
    # 执行处理逻辑
    result = f"处理结果: {user_input}"
    # 返回更新的状态
    return {"result": result}
```

### 2.3 边 (Edge)

边定义了节点之间的连接关系，决定了工作流的执行路径。LangGraph 支持两种类型的边：
- 普通边：直接连接两个节点
- 条件边：根据状态或返回值决定下一个执行的节点

### 2.4 工作流 (Workflow)

工作流是由节点和边组成的完整图，定义了整个处理流程。

## 3. 基本用法

### 3.1 创建状态图

```python
from langgraph.graph import StateGraph, END

# 创建状态图
workflow = StateGraph(MyState)
```

### 3.2 添加节点

```python
# 添加节点
workflow.add_node("process", process_node)
workflow.add_node("format", format_node)
```

### 3.3 添加边

```python
# 添加普通边
workflow.add_edge("process", "format")
workflow.add_edge("format", END)  # END 是一个特殊节点，表示工作流结束
```

### 3.4 添加条件边

在 LangGraph 中，条件边允许根据节点的返回值或状态动态决定下一个执行的节点。有两种主要方式配置条件边：

#### 3.4.1 使用路由函数

最简单的方式是提供一个路由函数，该函数接收状态和返回值，并返回下一个节点的名称：

```python
# 定义路由函数
def get_next_node(state, return_value):
    if "error" in return_value:
        return "error_handler"
    else:
        return "success_handler"

# 添加条件边
workflow.add_conditional_edges(
    "process",  # 源节点
    get_next_node  # 路由函数
)
```

这种方式简洁明了，适合大多数场景。路由函数必须返回一个有效的节点名称，该节点必须已经添加到工作流中。

#### 3.4.2 使用路由函数和条件映射（旧版本 API）

在某些版本的 LangGraph 中，`add_conditional_edges` 方法还支持第三个参数，即条件映射字典：

```python
# 添加条件边（旧版本 API）
workflow.add_conditional_edges(
    "process",  # 源节点
    router,     # 路由函数
    {
        "error_handler": lambda state, return_value: "error" in return_value,
        "success_handler": lambda state, return_value: "error" not in return_value
    }
)
```

但在最新版本中，推荐使用第一种方式，因为它更简洁且不易出错。

#### 3.4.3 处理复杂返回值

当节点返回复杂结构（如元组）时，路由函数需要正确处理：

```python
# 处理返回元组的节点
def route_tuple_return(state, return_value):
    # 检查返回值是否为元组，元组的第二个元素表示下一个节点
    if isinstance(return_value, tuple) and len(return_value) > 1:
        return return_value[1]  # 返回指定的下一个节点
    else:
        return "default_node"  # 默认节点
```

这种模式在实现自定义路由逻辑时非常有用，例如当节点可以返回状态更新和下一个节点的名称时。

### 3.5 设置入口点

```python
# 设置入口点
workflow.set_entry_point("process")
```

### 3.6 编译工作流

```python
# 编译工作流
compiled_workflow = workflow.compile()
```

### 3.7 执行工作流

```python
# 执行工作流
result = compiled_workflow.invoke({
    "messages": [],
    "user_input": "Hello, world!",
    "result": None
})
```

## 4. 高级用法

### 4.1 异步工作流

LangGraph 支持异步操作，可以使用 `async/await` 语法定义异步节点和执行异步工作流。

```python
async def async_node(state: MyState) -> dict:
    # 异步操作
    await asyncio.sleep(1)
    return {"result": "异步处理结果"}

# 异步执行工作流
result = await compiled_workflow.ainvoke(initial_state)
```

### 4.2 条件入口点

可以根据初始状态动态选择入口点。

```python
def entry_point_router(state):
    if state["user_input"].startswith("query:"):
        return "query_processor"
    else:
        return "general_processor"

workflow.set_conditional_entry_point(entry_point_router)
```

### 4.3 子图

可以将一个工作流作为另一个工作流的节点，实现模块化设计。

```python
# 创建子图
subgraph = StateGraph(SubState)
# 添加节点和边
subgraph.add_node("sub_process", sub_process_node)
subgraph.set_entry_point("sub_process")
subgraph.add_edge("sub_process", END)
compiled_subgraph = subgraph.compile()

# 在主图中使用子图
main_graph = StateGraph(MainState)
main_graph.add_node("subgraph", compiled_subgraph)
```

## 5. 最佳实践

### 5.1 状态设计

- 使用 `TypedDict` 或 Pydantic 模型明确定义状态结构
- 状态应包含工作流所需的所有信息，但避免冗余数据
- 考虑状态的序列化和反序列化需求

### 5.2 节点设计

- 节点应该是纯函数，避免副作用
- 节点应该专注于单一职责
- 节点应该明确声明其输入和输出

### 5.3 错误处理

- 在节点中捕获和处理异常
- 使用条件边处理错误路径
- 记录详细的错误信息

### 5.4 性能优化

- 对于 I/O 密集型操作，使用异步节点
- 考虑使用缓存减少重复计算
- 监控工作流执行时间，识别瓶颈

## 6. 常见问题及解决方案

### 6.1 导入问题

正确的导入方式：

```python
from langgraph.graph import StateGraph, END
```

不要使用不存在的模块或装饰器，如：

```python
# 错误的导入
from langgraph.graph.graph import graph  # 这个导入在新版本中不存在
```

### 6.2 节点返回值格式

节点函数应该返回一个字典，表示要更新的状态字段：

```python
def node(state):
    # 返回要更新的字段
    return {"result": "处理结果"}
```

对于条件路由，可以返回一个元组，包含状态更新和下一个节点的名称：

```python
def node(state):
    return {"result": "处理结果"}, "next_node_name"
```

### 6.3 工作流编译问题

确保在使用工作流之前调用 `compile()` 方法：

```python
compiled_workflow = workflow.compile()
result = compiled_workflow.invoke(initial_state)
```

### 6.4 条件边配置问题

在配置条件边时，常见的错误包括：

1. **未知目标节点错误**：当路由函数返回不存在的节点名称时，会出现 "unknown target" 错误。

   ```
   ValueError: At 'node_name' node, 'condition' branch found unknown target
   ```

   解决方法：确保路由函数返回的所有节点名称都已通过 `add_node` 方法添加到工作流中。

2. **API 使用错误**：不同版本的 LangGraph 可能有不同的 API。

   ```python
   # 错误：在新版本中使用旧版本的 API 格式
   workflow.add_edge("node_a", "node_b", condition=lambda state, return_value: True)  # 错误
   
   # 正确：使用 add_conditional_edges 方法
   workflow.add_conditional_edges("node_a", lambda state, return_value: "node_b")  # 正确
   ```

3. **返回值类型不一致**：路由函数必须处理所有可能的返回值类型。

   ```python
   # 正确处理不同类型的返回值
   def safe_router(state, return_value):
       if isinstance(return_value, tuple) and len(return_value) > 1:
           next_node = return_value[1]
           # 确保返回的节点名称是有效的
           if next_node in ["node_a", "node_b", "node_c"]:
               return next_node
       # 默认返回值
       return "default_node"
   ```

4. **忘记添加终止边**：工作流必须有明确的终止点。

   ```python
   # 添加到 END 节点的边
   workflow.add_edge("final_node", END)
   ```

修复这些问题的关键是：
- 确保所有节点都已添加到工作流中
- 使用正确版本的 API
- 路由函数处理所有可能的返回值类型
- 确保工作流有明确的终止点

## 7. 示例：简单的对话系统

```python
from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

# 定义状态
class ChatState(TypedDict):
    messages: List[Dict[str, str]]
    response: Optional[str]

# 创建状态图
workflow = StateGraph(ChatState)

# 定义节点
async def process_message(state: ChatState) -> dict:
    messages = state["messages"]
    last_message = messages[-1]["content"] if messages else ""
    response = f"Echo: {last_message}"
    return {"response": response}

async def update_history(state: ChatState) -> dict:
    messages = state["messages"].copy()
    response = state["response"]
    messages.append({"role": "assistant", "content": response})
    return {"messages": messages}

# 添加节点
workflow.add_node("process", process_message)
workflow.add_node("update", update_history)

# 添加边
workflow.add_edge("process", "update")
workflow.add_edge("update", END)

# 设置入口点
workflow.set_entry_point("process")

# 编译工作流
compiled_workflow = workflow.compile()

# 使用工作流
initial_state = {
    "messages": [{"role": "user", "content": "Hello, world!"}],
    "response": None
}
result = compiled_workflow.invoke(initial_state)
print(result)
```

## 8. 总结

LangGraph 是一个强大的工具，用于构建复杂的语言处理工作流。通过正确理解和使用其核心概念和 API，可以构建灵活、可维护的语言处理系统。关键是要遵循最佳实践，特别是在状态设计、节点实现和错误处理方面。

## 参考资料

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 文档](https://python.langchain.com/docs/get_started/introduction) 