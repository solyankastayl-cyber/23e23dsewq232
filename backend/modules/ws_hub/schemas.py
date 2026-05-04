"""
WebSocket Message Schemas
Sprint WS-1: Unified envelope for all WS messages
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SubscribeMessage(BaseModel):
    type: Literal["subscribe"]
    channels: List[str] = Field(default_factory=list)


class UnsubscribeMessage(BaseModel):
    type: Literal["unsubscribe"]
    channels: List[str] = Field(default_factory=list)


class SubscribedMessage(BaseModel):
    type: Literal["subscribed"] = "subscribed"
    channels: List[str]
    version: int = 1
    ts: int


class EventMessage(BaseModel):
    type: Literal["event"] = "event"
    channel: str
    event: str
    version: int = 1
    ts: int
    data: Dict[str, Any]


class SnapshotMessage(BaseModel):
    type: Literal["snapshot"] = "snapshot"
    channel: str
    version: int = 1
    ts: int
    data: Any


class HeartbeatMessage(BaseModel):
    type: Literal["heartbeat"] = "heartbeat"
    ts: int


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
    ts: int
