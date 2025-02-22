from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field

class ContentType(BaseModel):
    """Base content type model"""
    type: str = Field(..., description="Content type")

class TextContent(ContentType):
    """Text content type"""
    type: Literal["text"] = Field("text", description="Text content type")
    text: str = Field(..., description="Text content")

class ImageURLObject(BaseModel):
    """Image URL object"""
    url: str = Field(..., description="Image URL")

class ImageContent(ContentType):
    """Image content type"""
    type: Literal["image"] = Field("image", description="Image content type")
    image_url: ImageURLObject = Field(..., description="Image URL object")

class Message(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Message role: system, user, assistant")
    content: Union[str, List[Union[TextContent, ImageContent]]] = Field(
        ..., 
        description="Message content - either a string or a list of content objects"
    )
    name: Optional[str] = Field(None, description="Optional name of the message sender")

class ChatCompletionRequest(BaseModel):
    """Chat completion request model"""
    model: str = Field(..., description="Model name to use")
    messages: List[Message] = Field(..., description="List of messages")
    temperature: Optional[float] = Field(0.7, description="Temperature parameter, controls randomness")
    top_p: Optional[float] = Field(1.0, description="Top-p sampling parameter")
    n: Optional[int] = Field(1, description="Number of responses to generate")
    stream: Optional[bool] = Field(False, description="Whether to use streaming response")
    stop: Optional[List[str]] = Field(None, description="List of tokens to stop generation")
    max_tokens: Optional[int] = Field(None, description="Maximum number of tokens to generate")

class Choice(BaseModel):
    """Generated choice model"""
    index: int = Field(..., description="Choice index")
    message: Message = Field(..., description="Generated message")
    finish_reason: Optional[str] = Field(None, description="Reason for completion")

class ChatCompletionResponse(BaseModel):
    """Chat completion response model"""
    id: str = Field(..., description="Response ID")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[Choice] = Field(..., description="List of generated choices")

class StreamChoice(BaseModel):
    """Stream response choice model"""
    index: int = Field(..., description="Choice index")
    delta: Dict[str, str] = Field(..., description="Incremental content")
    finish_reason: Optional[str] = Field(None, description="Reason for completion")

class ChatCompletionStreamResponse(BaseModel):
    """Chat completion stream response model"""
    id: str = Field(..., description="Response ID")
    object: str = Field("chat.completion.chunk", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[StreamChoice] = Field(..., description="List of generated choices") 