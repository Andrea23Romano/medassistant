from pydantic import BaseModel, Field
from datetime import datetime, date
import uuid
from typing import List, Optional


class Message(BaseModel):
    """Schema for a single chat message compatible with OpenAI API"""

    role: str
    content: str
    name: Optional[str] = None
    function_call: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationEntry(BaseModel):
    """Schema for conversations with hybrid search support"""

    session_id: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: List[Message] = []
    document_ids: List[str] = []
    model_params: dict = {}
    text_content: Optional[str] = None
    embedding: Optional[List[float]] = None
    keywords: List[str] = []


class SummaryEntry(BaseModel):
    """Schema for daily summaries"""

    summary_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    day: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    summary: str
    session_ids: List[str] = []
    document_ids: List[str] = []
    model_params: dict = {}
    embedding: Optional[List[float]] = None
    keywords: List[str] = []


class DocumentEntry(BaseModel):
    """Schema for user uploaded documents"""

    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    text: str
    images: List[str] = []
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    embedding: Optional[List[float]] = None
    keywords: List[str] = []


class User(BaseModel):
    """Schema for user data"""

    user_id: str
    name: str
    email: str
    password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
