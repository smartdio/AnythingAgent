# Deep Analyzer 模型需求文档

## 1. 概述

Deep Analyzer 是一个基于 CrewAI 框架实现的高级分析模型，旨在深入分析用户消息和系统消息，判断信息是否足够，并根据分析结果进行任务分解和执行。该模型将作为 AnythingAgent 平台的一部分，提供更智能的上下文管理和任务处理能力。

## 2. 系统架构

Deep Analyzer 模型基于流程图设计，包含以下主要组件：

1. **Analyzer**：分析用户消息和系统消息，判断信息是否足够
2. **Planner**：当信息足够时，负责分解任务计划
3. **Worker**：执行具体任务，并将结果添加到结果集

## 3. 工作流程

1. 用户发送消息到系统
2. Analyzer 组件接收用户消息和系统消息
3. Analyzer 分析信息是否足够：
   - 如果不足够，向用户询问更多信息
   - 如果足够，返回 NEXT-AGENT 标识，并将控制权交给 Planner
4. Planner 根据分析结果制定分步任务计划
5. Worker 按照计划执行任务
6. 执行结果添加到结果集
7. 如果还有任务，Worker 继续执行；否则，流程结束

## 4. 技术实现

### 4.1 CrewAI 框架集成

Deep Analyzer 模型将使用 CrewAI 框架实现，主要包括：

1. **Agent 定义**：
   - Analyzer Agent：负责分析信息
   - Planner Agent：负责任务规划
   - Worker Agent：负责任务执行

2. **Task 定义**：
   - 分析任务：分析用户和系统消息
   - 规划任务：分解任务计划
   - 执行任务：执行具体任务

3. **Crew 定义**：
   - 将上述 Agent 和 Task 组织成一个协作团队
   - 使用 Sequential Process 流程管理任务执行顺序

### 4.2 与 AnythingAgent 集成

Deep Analyzer 模型将作为 AnythingBaseModel 的子类实现，遵循以下接口：

1. **on_chat_messages**：处理聊天消息的主要方法
2. **on_chat_start**：聊天开始时的钩子方法
3. **on_chat_end**：聊天结束时的钩子方法

### 4.3 任务分解格式

任务分解将使用 YAML 格式返回，例如：

```yaml
task1:
  title: 任务标题1
  prompt: 任务描述1
task2:
  title: 任务标题2
  prompt: 任务描述2
```

## 5. 依赖项

- CrewAI 框架
- 现有的 AnythingAgent 平台组件
- 向量数据库支持（用于上下文检索）

## 6. 实现计划

1. 安装 CrewAI 依赖
2. 创建 Deep Analyzer 模型基础结构
3. 实现 Analyzer、Planner 和 Worker 组件
4. 集成到 AnythingAgent 平台
5. 测试和优化

## 7. 预期效果

1. 能够智能分析用户输入，判断信息是否足够
2. 能够自动分解复杂任务为可执行的子任务
3. 能够按照计划顺序执行任务
4. 能够与用户进行自然交互，询问必要信息
5. 能够将执行结果整合并返回给用户 