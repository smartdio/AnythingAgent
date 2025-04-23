from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Callable, Awaitable
import json
import asyncio
import inspect

from app.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionStreamResponse,
    Message,
    Choice,
    StreamChoice
)
from app.utils.common import generate_id, get_current_timestamp, format_error_response
from app.core.config import settings
from app.models.manager import model_manager
from app.core.logger import get_logger

logger = get_logger("chat")
router = APIRouter()

async def safe_call_method(model: object, method_name: str, *args, **kwargs):
    """
    Safely call a model's method, ignore if the method doesn't exist.
    
    Args:
        model: Model instance
        method_name: Method name
        *args: Positional arguments
        **kwargs: Keyword arguments
    """
    method = getattr(model, method_name, None)
    if method and inspect.iscoroutinefunction(method):
        await method(*args, **kwargs)

@router.post("/chat/completions", 
            response_model=ChatCompletionResponse,
            responses={
                400: {"model": dict},
                401: {"model": dict}
            })
async def create_chat_completion(
    request: Request,
    chat_request: ChatCompletionRequest,
) -> ChatCompletionResponse:
    """
    Create chat completion.

    Args:
        request: Raw request object
        chat_request: Chat completion request.

    Returns:
        Chat completion response.
    """
    try:
        # Log request information
        body = await request.body()
        headers = dict(request.headers)
        logger.info("Received chat request:")
        logger.info(f"Headers: {json.dumps(headers, ensure_ascii=False, indent=2)}")
        logger.info(f"Body: {body.decode()}")
        logger.info(f"Parsed Request: {chat_request.model_dump_json(indent=2)}")

        # Get model instance
        model = model_manager.get_model(chat_request.model)
        if not model:
            logger.error(f"Model {chat_request.model} not found")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model {chat_request.model} not found"
            )

        # Start chat (optional method)
        await safe_call_method(model, "on_chat_start")

        if chat_request.stream:
            logger.info("Using streaming response mode")
            return StreamingResponse(
                _stream_chat_completion(chat_request, model),
                media_type="text/event-stream"
            )

        # Process messages (non-streaming)
        logger.info("Using normal response mode")
        response_content = await model.on_chat_messages(
            chat_request.messages
        )

        # Build response
        response_id = generate_id("chatcmpl-")
        response = ChatCompletionResponse(
            id=response_id,
            created=get_current_timestamp(),
            model=chat_request.model,
            choices=[
                Choice(
                    index=0,
                    message=Message(
                        role="assistant",
                        content=response_content
                    ),
                    finish_reason="stop"
                )
            ]
        )
        
        # Log response information
        logger.info(f"Response content: {response.model_dump_json(indent=2)}")
        return response

    except Exception as e:
        # Ensure on_chat_end is called even when error occurs (optional method)
        if 'model' in locals():
            await safe_call_method(model, "on_chat_end")
        logger.error(f"Error in chat completion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

async def _stream_chat_completion(
    request: ChatCompletionRequest,
    model: 'AnythingBaseModel'
) -> AsyncGenerator[str, None]:
    """
    Streaming chat completion generator.

    Args:
        request: Chat completion request.
        model: Model instance.

    Yields:
        Streaming response data.
    """
    response_id = generate_id("chatcmpl-")
    response_queue = asyncio.Queue()
    logger.info(f"Starting streaming response, ID: {response_id}")
    
    try:
        # First send a role message
        start_response = ChatCompletionStreamResponse(
            id=response_id,
            created=get_current_timestamp(),
            model=request.model,
            choices=[
                StreamChoice(
                    index=0,
                    delta={"role": "assistant"},
                    finish_reason=None
                )
            ]
        )
        yield f"data: {start_response.model_dump_json()}\n\n"
        logger.info("Role message sent")

        async def send_chunk(content: str, is_reasoning: bool = False):
            """Callback function for sending streaming content"""
            logger.debug(f"Received model generated content: {'reasoning' if is_reasoning else 'content'}: {content}")
            await response_queue.put((content, is_reasoning))

        # Start model's streaming process
        logger.info("Starting model processing task")
        try:
            process_task = asyncio.create_task(
                model.on_chat_messages(
                    request.messages,
                    callback=send_chunk
                )
            )
        except TypeError as e:
            # 处理旧版模型不支持 is_reasoning 参数的情况
            logger.warning(f"Model doesn't support reasoning_content parameter: {str(e)}")
            # 定义向后兼容的回调函数
            async def backwards_compatible_callback(content: str):
                await send_chunk(content, False)  # 默认为非推理内容
            
            process_task = asyncio.create_task(
                model.on_chat_messages(
                    request.messages,
                    callback=backwards_compatible_callback
                )
            )
        
        # Continuously get and send responses from queue
        chunk_count = 0
        while not process_task.done() or not response_queue.empty():
            try:
                # Get content and type (reasoning or normal content)
                content_data = await asyncio.wait_for(response_queue.get(), timeout=0.5)
                
                # Check if it's a tuple (new format) or just a string (old format for backward compatibility)
                if isinstance(content_data, tuple):
                    content, is_reasoning = content_data
                else:
                    content, is_reasoning = content_data, False
                    
                chunk_count += 1
                
                # Create delta based on content type
                delta = {"reasoning_content": content} if is_reasoning else {"content": content}
                
                # Build streaming response
                response = ChatCompletionStreamResponse(
                    id=response_id,
                    created=get_current_timestamp(),
                    model=request.model,
                    choices=[
                        StreamChoice(
                            index=0,
                            delta=delta,
                            finish_reason=None
                        )
                    ]
                )
                
                # Send data
                chunk_data = f"data: {response.model_dump_json()}\n\n"
                logger.debug(f"Sending chunk #{chunk_count}: {content}")
                yield chunk_data
                
            except asyncio.TimeoutError:
                logger.debug("Timeout waiting for new content")
                continue
            except Exception as e:
                logger.error(f"Error processing data chunk: {str(e)}")
                raise

        # Check for errors
        if process_task.exception():
            logger.error(f"Model processing error: {process_task.exception()}")
            raise process_task.exception()
        
        # Send end marker
        logger.info(f"Streaming response completed, sent {chunk_count} chunks")
        
        # Send end marker
        end_response = ChatCompletionStreamResponse(
            id=response_id,
            created=get_current_timestamp(),
            model=request.model,
            choices=[
                StreamChoice(
                    index=0,
                    delta={},
                    finish_reason="stop"
                )
            ]
        )
        yield f"data: {end_response.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
        logger.info("End marker sent")
        
    except Exception as e:
        logger.error(f"Error in streaming response process: {str(e)}")
        raise
    finally:
        # Ensure on_chat_end is called when generator ends (optional method)
        await safe_call_method(model, "on_chat_end") 