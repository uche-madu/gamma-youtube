# app/models/state.py
from typing import List
from pydantic import BaseModel
from langgraph.prebuilt.chat_agent_executor import AgentState

# Extend the AgentState with our workflow state fields.
class State(AgentState):
    transcript: str       # Full transcript from get_youtube_transcript
    contents: List[str]   # Transcript chunks for summarization
    index: int            # Current index for iterative summarization
    summary: str          # Accumulated summary

# Pydantic models for API request and response
class QueryRequest(BaseModel):
    query: str
    tts: bool | None = False

class SummarizationResponse(BaseModel):
    title: str
    summary: str
    video_link: str | None = None
    audio_url: str | None = None
