from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class MessagePart(BaseModel):
    kind: str
    text: Optional[str] = None
    file_url: Optional[str] = None
    file_bytes: Optional[str] = None


class Message(BaseModel):
    kind: str
    role: str
    parts: List[MessagePart]
    messageId: Optional[str]
    taskId: Optional[str] = None


class Params(BaseModel):
    message: Message
    configuration: Optional[Dict[str, Any]] = None


class RPCRequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: Params


class RPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
