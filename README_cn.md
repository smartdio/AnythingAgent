# AnythingAgent

**一切皆可 Agent**

![Logo](doc/images/logo.jpg)

AnythingAgent 的想法很简单，就是把一切应用功能都变成智能体。使用任何功能都像聊天一样简单。

[English](README.md) | 简体中文


AnythingAgent 通过 AnythingModel 和 AnythingMCP 两种接口形式为外部系统（如聊天机器人、智能代理、AI流程控制系统等）提供服务。 API 设计完全兼容 OpenAI API，可以无缝地与大多数 AI 应用集成。

![AnythingAgent](doc/images/anythingagent.png)


## 主要特性

- OpenAI 兼容：API 端点和请求格式完全兼容 OpenAI，支持直接替换
- 文件管理系统：支持多种文件格式的上传、下载和管理，API 格式与 OpenAI 文件管理接口一致
- API 密钥认证：采用与 OpenAI 相同的 Bearer Token 认证机制
- 异步处理：基于 FastAPI 的高性能异步处理
- 向量存储：使用 LanceDB 进行高效的向量存储和检索
- 封装模型：通过简单的 AnythingBaseModel 实现应用到模型的无缝集成
- 模型管理：通过简单的模型管理接口实现模型的管理，无限扩展
- 兼容各种ChatUI：支持各种ChatUI，如 Streamlit, Gradio, Flask, etc.
- 虚拟环境：每个模型运行在一个独立的虚拟环境中，互不干扰

## 开发路线

- [x] 实现兼容 OpenAI 的 API 接口
- [x] 实现模型的规范
- [x] 实现模型的部署管理
- [ ] 支持消息中包含图片和文件
- [ ] 实现多种 LLM 的代理模型
- [ ] 实现一批基本模型
- [ ] 实现MCP 接口
- [ ] 实现权限管理
- [ ] 实现用户和Key管理


## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

在 `.env` 文件中配置必要的参数：

```env
# API配置
ENABLE_API_KEY=false
API_KEY=your-api-key

# 文件配置
MAX_FILE_SIZE=52428800

# 模型配置
MODEL_DIR=models
```

### 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 模型的开发

新建一个文件夹，如 `models/my_model`，然后新建一个文件 `main.py`，实现一个模型，只需要继承 AnythingBaseModel 类，并实现 `on_chat_message` 方法。

```python
class MyModel(AnythingBaseModel):
    def on_chat_message(self, message: str,callback: Callable):
        # 处理消息
        callback(message)
```

### 模型部署

把开发完成的模型文件夹，如 `models/my_model`，复制到 `models` 文件夹下。



### 模型的管理

模型管理通过简单的模型管理接口实现模型的管理，无限扩展。


## API 使用说明

所有 API 端点和请求格式都与 OpenAI API 保持一致，可以直接使用各种 OpenAI API 客户端库，只需修改 base URL。


### 支持的文件类型

- 文档：pdf, doc, docx, xls, xlsx, ppt, pptx
- 图片：jpg, jpeg, png, gif, bmp, webp, svg
- 文本：txt, json, csv, md, yaml, yml

## 开发说明

项目使用 Python 3.10+ 开发，主要依赖：

- FastAPI：Web框架
- LanceDB：向量数据库
- Pydantic：数据验证
- aiofiles：异步文件操作

API文档访问：
- Swagger UI: http://localhost:8000/v1/docs
- ReDoc: http://localhost:8000/v1/redoc 

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
