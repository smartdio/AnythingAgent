	1.	外部系统（如 ChatBot）通过 POST /v1/chat/completions 接口提交消息：
	•	外部应用向 AnythingModel 端点提交请求，并指定所选模型名称（model）。
	•	请求中包括对话消息数据（messages）以及其他可能的参数（如 temperature、max_tokens 等）。
	2.	AnythingModel 根据模型名称选择模型：
	•	在接收到请求后，AnythingModel 会根据 model 参数，从注册的模型库中选择合适的模型来处理消息。
	•	这些模型都继承自 AnythingBaseModel，并需要实现至少一个核心方法——OnChatMessages。
	3.	流式返回内容：
	•	模型根据处理的结果，以流式返回内容（比如逐步生成的文本）。
	•	这一过程通常是通过将消息分批返回或更新内容来实现的，保持响应流的持续性。
	4.	AnythingBaseModel 的方法实现：
	•	OnChatMessages(messages)：这是每个模型必须实现的关键方法，用于接收输入消息并生成响应。可以根据不同模型的需求进行实现。
	•	其他可选方法如：
	•	OnChatStart()：开始聊天时调用。
	•	OnChatStop()：停止聊天时调用。
	•	OnChatEnd()：结束聊天时调用。
	•	OnChatResume(thread)：恢复聊天（如果支持多线程聊天的话）。

通过这种设计，AnythingModel 充当了模型注册和选择的管理者，负责确保对话消息被路由到合适的模型，并根据模型的处理结果进行流式响应。
