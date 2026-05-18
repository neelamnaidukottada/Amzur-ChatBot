"""Pydantic schemas for chat API requests and responses."""

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message."""

    user_message: str = Field(..., min_length=1, max_length=10000)


class ChatMessageResponse(BaseModel):
    """Response schema for chat message response."""

    user_message: str
    assistant_response: str


class DatabaseQuestionRequest(BaseModel):
    """Request schema for asking natural-language questions over a SQL database."""

    database_url: str | None = Field(default=None, min_length=8, max_length=1000)
    question: str = Field(..., min_length=1, max_length=10000)
    conversation_id: int | None = None


class DatabaseQuestionResponse(BaseModel):
    """Response schema for SQL database question answering."""

    user_message: str
    assistant_response: str
    generated_sql: str


class DataframeQuestionResponse(BaseModel):
    """Response schema for dataframe/CSV question answering."""

    user_message: str
    assistant_response: str
    source: str | None = None
    row_count: int | None = None
    columns: list[str] | None = None
