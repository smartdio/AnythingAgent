# 提示词组装逻辑分析

本文档详细解释了 DeepAnalyzerModel 中提示词的组装逻辑。

## 整体流程

DeepAnalyzerModel 的提示词组装分为三个主要阶段：

1. **分析阶段**：判断用户提供的信息是否足够
2. **规划阶段**：将任务分解为子任务
3. **执行阶段**：执行每个子任务并返回结果

## 提示词来源

提示词有两个主要来源：
1. **配置文件**：从 `config.yaml` 中读取
2. **默认模板**：从 `templates.py` 中导入的默认模板

## 详细组装逻辑

### 1. 分析阶段提示词组装

```python
# 创建分析任务提示词
analyze_task_template = ""
if "analyze_task" in task_templates and isinstance(task_templates["analyze_task"], dict) and "description" in task_templates["analyze_task"]:
    analyze_task_template = task_templates["analyze_task"]["description"]
    # 日志记录...
else:
    # 使用默认模板
    analyze_task_template = DEFAULT_ANALYZE_TASK_TEMPLATE

# 格式化模板
analyze_task_description = analyze_task_template.format(
    history_context=history_context,
    user_message=user_message,
    system_message=system_message
)

# 构建系统提示词
analyzer_system_prompt = DEFAULT_ANALYZER_SYSTEM_PROMPT.format(
    analyzer_role=analyzer_role,
    analyzer_backstory=analyzer_backstory,
    analyzer_goal=analyzer_goal
)
```

这里的逻辑是：
1. 尝试从配置文件中获取分析任务模板
2. 如果配置文件中没有或格式不正确，则使用默认模板
3. 使用 `format()` 方法填充模板中的变量
4. 构建系统提示词，插入角色、背景故事和目标

### 2. 规划阶段提示词组装

```python
# 创建规划任务提示词
planning_task_template = ""
if "planning_task" in task_templates and isinstance(task_templates["planning_task"], dict) and "description" in task_templates["planning_task"]:
    planning_task_template = task_templates["planning_task"]["description"]
    # 日志记录...
else:
    # 使用默认模板
    planning_task_template = DEFAULT_PLANNING_TASK_TEMPLATE

# 格式化模板
planning_task_description = planning_task_template.format(
    history_context=history_context,
    user_message=user_message
)

# 构建系统提示词
planner_system_prompt = DEFAULT_PLANNER_SYSTEM_PROMPT.format(
    planner_role=planner_role,
    planner_backstory=planner_backstory,
    planner_goal=planner_goal
)
```

规划阶段的逻辑与分析阶段类似，但注意规划任务模板只需要历史上下文和用户消息，不需要系统消息。

### 3. 执行阶段提示词组装

```python
# 构建系统提示词
worker_system_prompt = DEFAULT_WORKER_SYSTEM_PROMPT.format(
    worker_role=worker_role,
    worker_backstory=worker_backstory,
    worker_goal=worker_goal
)

# 创建执行任务提示词
execution_task_template = ""
if "execution_task" in task_templates and isinstance(task_templates["execution_task"], dict) and "description" in task_templates["execution_task"]:
    execution_task_template = task_templates["execution_task"]["description"]
    # 日志记录...
else:
    # 使用默认模板
    execution_task_template = DEFAULT_EXECUTION_TASK_TEMPLATE

# 对每个任务进行格式化
execution_task_description = execution_task_template.format(
    history_context=history_context,
    task_title=task_title,
    task_prompt=task_prompt
)
```

执行阶段的特点是需要为每个子任务单独格式化提示词，插入任务标题和任务描述。

## 提示词变量说明

1. **历史上下文 (history_context)**：
   - 包含最近的对话历史（最多10条消息）
   - 格式为 "用户: 内容" 和 "助手: 内容"

2. **用户消息 (user_message)**：
   - 当前用户的输入消息

3. **系统消息 (system_message)**：
   - 从消息列表中提取的所有系统消息，用换行符连接

4. **任务相关变量**：
   - task_title: 子任务的标题
   - task_prompt: 子任务的详细描述

5. **角色相关变量**：
   - analyzer_role/planner_role/worker_role: 各阶段的角色名称
   - analyzer_backstory/planner_backstory/worker_backstory: 各角色的背景故事
   - analyzer_goal/planner_goal/worker_goal: 各角色的目标

## 错误处理和回退机制

代码中实现了完善的错误处理和回退机制：

1. 如果配置文件中没有提供模板，使用默认模板
2. 如果模板格式不正确，使用默认模板
3. 如果任务解析失败，创建默认任务
4. 如果任务缺少必要字段，尝试从其他字段获取或创建默认值

这确保了即使配置有问题，系统仍然能够正常工作。

## 日志记录

代码中大量使用了日志记录，记录了：
1. 模板的来源（配置文件或默认）
2. 模板的长度和前200个字符
3. 发送给LLM的系统提示词和用户提示词
4. LLM的响应结果

这些日志对于调试和优化提示词非常有帮助。 