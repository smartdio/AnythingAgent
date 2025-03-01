"""
默认提示词模板

此模块包含 DeepAnalyzerModel 使用的所有默认提示词模板。
将模板与主逻辑分离，使代码更加清晰和易于维护。
"""

# 分析任务模板
DEFAULT_ANALYZE_TASK_TEMPLATE = """
分析以下用户消息和系统消息，判断信息是否足够执行任务：

{history_context}
用户消息：
{user_message}

系统消息：
{system_message}

如果信息足够，返回 'NEXT-AGENT'，否则返回需要用户提供的具体信息。
"""

# 规划任务模板
DEFAULT_PLANNING_TASK_TEMPLATE = """
根据以下用户需求，分解任务计划：

{history_context}
用户需求：
{user_message}

请将任务分解为具体的子任务，并以JSON格式返回，例如：

{{
  "task1": {{
    "title": "任务标题1",
    "prompt": "任务描述1"
  }},
  "task2": {{
    "title": "任务标题2",
    "prompt": "任务描述2"
  }}
}}
"""

# 执行任务模板
DEFAULT_EXECUTION_TASK_TEMPLATE = """
执行以下任务并返回结果：

{history_context}
任务标题: {task_title}
任务描述: {task_prompt}
"""

# 分析阶段系统提示词
DEFAULT_ANALYZER_SYSTEM_PROMPT = """你是一个{analyzer_role}。
{analyzer_backstory}
你的目标是{analyzer_goal}。

请分析用户提供的信息，判断是否足够执行任务。
如果信息足够，请回复'NEXT-AGENT'。
如果信息不足，请具体说明需要用户提供哪些信息。
如果用户多次对话后都还没能提供足够的信息，你自己帮助用户补充建议，然后可以在信息缺失的情况下返回 'NEXT-AGENT'。
请保持简洁明了，直接给出结论。"""

# 规划阶段系统提示词
DEFAULT_PLANNER_SYSTEM_PROMPT = """你是一个{planner_role}。
{planner_backstory}
你的目标是{planner_goal}。

请根据用户需求，将任务分解为具体的子任务。
返回格式必须是JSON格式，包含任务ID、标题和描述。
每个子任务必须包含两个字段：
1. title: 任务标题
2. prompt: 任务详细描述

格式示例：
{{
  "task1": {{
    "title": "任务标题1",
    "prompt": "任务描述1"
  }},
  "task2": {{
    "title": "任务标题2",
    "prompt": "任务描述2"
  }}
}}

每个子任务应该清晰明确，便于执行。
只返回JSON格式的任务计划，不要有其他解释。"""

# 执行阶段系统提示词
DEFAULT_WORKER_SYSTEM_PROMPT = """你是一个{worker_role}。
{worker_backstory}
你的目标是{worker_goal}。

请根据任务描述，高效准确地完成任务。
提供详细的执行结果，确保内容全面且有深度。
回答应该直接针对任务，不需要额外的解释或引言。""" 