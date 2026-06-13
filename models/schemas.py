from typing import Literal

from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    document_id: str
    file_url: str
    file_type: str
    user_id: str


class DeleteVectorsRequest(BaseModel):
    document_id: str
    user_id: str


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class QueryRequest(BaseModel):
    document_id: str
    question: str
    user_id: str
    mode: Literal["default", "plain_english", "conversational"] = "conversational"
    history: list[ChatTurn] = Field(default_factory=list)


class QuerySource(BaseModel):
    content: str
    chunk_index: int
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[QuerySource]
    confidence: str
    irrelevant: bool = False


class PortfolioQueryRequest(BaseModel):
    question: str
    user_id: str
    document_ids: list[str]
    document_titles: dict[str, str] = Field(default_factory=dict)


class PortfolioSource(BaseModel):
    content: str
    chunk_index: int
    document_id: str
    document_title: str
    score: float


class PortfolioQueryResponse(BaseModel):
    answer: str
    sources: list[PortfolioSource]
    confidence: str
    documents_searched: int
