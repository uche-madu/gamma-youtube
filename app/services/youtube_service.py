# app/services/youtube_service.py
import asyncio
from typing_extensions import Annotated
from decouple import config
from serpapi import GoogleSearch
from youtube_transcript_api import YouTubeTranscriptApi # type: ignore
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langchain_core.messages import ToolMessage

from app.utils.threading_utils import run_in_executor
from app.config import SERPAPI_API_KEY



@tool
async def search_youtube_video(title: str):
    """
    Search for a YouTube video based on a given title.

    Use this tool when you need to find a relevant YouTube video before retrieving its transcript.
    This tool returns the title, video link, and video ID, which can then be used for fetching the transcript.

    Input:
    - title: The search query for the YouTube video.

    Output:
    - A dictionary with:
      - 'title': The video title.
      - 'link': The direct URL to the video.
      - 'video_id': The unique YouTube video ID for transcript retrieval.
    """
    params = {
        "engine": "youtube",
        "search_query": title,
        "api_key": SERPAPI_API_KEY
    }
    search = GoogleSearch(params)
    
    # Run search in an async-compatible way
    results = await run_in_executor(search.get_dict)

    if "video_results" in results:
        video = results["video_results"][0]  # Get the first result
        return {
            "title": video["title"],
            "link": video["link"],
            "video_id": video["link"].split("v=")[-1]
        }
    return None


@tool
async def get_youtube_transcript(
    video_id: str,
    tool_call_id: Annotated[str, InjectedToolCallId], 
    config: RunnableConfig, 
):
    """
    Asynchronously fetch the transcript for a YouTube video.
    
    Use this tool when you have a video_id and need to retrieve the full transcript.
    The returned transcript may be very long and should be processed further.
    
    Input:
    - video_id: The unique identifier for the YouTube video.
    
    Output:
    - A string containing the full transcript.
    """
    try:
        raw_transcript = await run_in_executor(lambda: YouTubeTranscriptApi.get_transcript(video_id))
        transcript = " ".join([t["text"] for t in raw_transcript])
        return Command(
            update={
                "transcript": transcript,
                "messages": [
                    ToolMessage(
                        "Successfully added transcript to State", tool_call_id=tool_call_id
                    )
                ]
            },
        )
    except Exception as e:
        return f"Transcript not available: {e}"
