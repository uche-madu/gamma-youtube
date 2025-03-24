# app/services/youtube_service.py
from typing_extensions import Annotated
from serpapi import GoogleSearch
from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
from youtube_transcript_api.proxies import WebshareProxyConfig
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langchain_core.messages import ToolMessage

from app.utils.threading_utils import run_in_executor
from app.settings import settings
from loguru import logger
import yt_dlp
import requests

@tool
async def search_youtube_video(title: str):
    """Search for a YouTube video based on a given title.

    Use this tool when you need to find a relevant YouTube video before retrieving its transcript.
    This tool returns the title, video link, and video ID, which can then be used for fetching the transcript.

    Args:
        title (str): The search query for the YouTube video.

    Returns:
        dict: A dictionary containing:
            - 'title' (str): The video title.
            - 'link' (str): The direct URL to the video.
            - 'video_id' (str): The unique YouTube video ID for transcript retrieval.
        None: If no video results are found.
    """
    logger.info(f"Searching for YouTube video with title: {title}")
    params = {
        "engine": "youtube",
        "search_query": title,
        "api_key": settings.SERPAPI_API_KEY
    }
    search = GoogleSearch(params)

    try:
        results = await run_in_executor(search.get_dict)
        if "video_results" in results:
            video = results["video_results"][0]
            logger.info(f"Found video: {video['title']} with ID: {video['link'].split('v=')[-1]}")
            return {
                "title": video["title"],
                "link": video["link"],
                "video_id": video["link"].split("v=")[-1]
            }
        else:
            logger.warning("No video results found.")
            return None
    except Exception as e:
        logger.error(f"Error during YouTube search: {e}")
        return None

@tool
async def get_youtube_transcript(
    video_id: str,
    tool_call_id: Annotated[str, InjectedToolCallId], 
    config: RunnableConfig, 
):
    """Asynchronously fetch the transcript for a YouTube video.

    Use this tool when you have a video_id and need to retrieve the full transcript.
    The returned transcript may be very long and should be processed further.

    Args:
        video_id (str): The unique identifier for the YouTube video.
        tool_call_id (str): The tool call identifier for tracking purposes.
        config (RunnableConfig): Configuration for the runnable environment.

    Returns:
        Command: An object containing the transcript and a success message.
        str: An error message if the transcript is not available.
    """
    logger.info(f"Fetching transcript for video ID: {video_id}")
    try:
        ytt_api = YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=settings.WEBSHARE_PROXY_USERNAME, # type: ignore
                proxy_password=settings.WEBSHARE_PROXY_PASSWORD, # type: ignore
            )
        )
        raw_transcript = await run_in_executor(lambda: ytt_api.get_transcript(video_id))
        transcript = " ".join([t["text"] for t in raw_transcript])
        logger.info(f"Successfully fetched transcript for video ID: {video_id}")
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
        logger.error(f"Error fetching transcript for video ID {video_id}: {e}")
        return f"Transcript not available: {e}"


# async def get_youtube_transcript_url(video_url: str) -> str | None:
#     """Fetches the transcript URL for a given YouTube video url."""
#     logger.info(f"Fetching transcript URL for video ID: {video_url}")
#     ydl_opts = {
#         'skip_download': True,
#         'quiet': True,
#         'writesubtitles': True,
#         'subtitleslangs': ['en'],  # Use ['auto'] for automatic captions
#         'writeautomaticsub': True,
#     }
#     try:
#         info = await run_in_executor(lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(video_url, download=False))
#         if info:
#             subtitles = info.get('subtitles') or info.get('automatic_captions')
#         else:
#             subtitles = None
#         if subtitles and 'en' in subtitles:
#             return subtitles['en'][0]['url']
#         return None
#     except Exception as e:
#         logger.error(f"Error fetching transcript URL for video URL {video_url}: {e}")
#         return None


# async def fetch_transcript(transcript_url: str) -> str:
#     """Downloads and extracts text from a YouTube transcript URL."""
#     if not transcript_url:
#         return "No transcript available"

#     try:
#         response = await run_in_executor(lambda: requests.get(transcript_url))
#         if response.status_code == 200:
#             transcript_data = response.json()
#             transcript_text = " ".join(
#                 " ".join(seg["utf8"] for seg in entry["segs"])  # Extract all words
#                 for entry in transcript_data["events"] 
#                 if "segs" in entry
#             )
#             return transcript_text
#     except Exception as e:
#         logger.error(f"Error fetching transcript content: {e}")
    
#     return "No transcript found"

# @tool
# async def get_youtube_transcript(
#     video_link: str,
#     tool_call_id: Annotated[str, InjectedToolCallId], 
#     config: RunnableConfig, 
# ):
#     """Asynchronously fetch the transcript for a YouTube video.

#     Use this tool when you have a video link and need to retrieve the full transcript.
#     The returned transcript may be very long and should be processed further.

#     Args:
#         video_link (str): The full YouTube video URL.
#         tool_call_id (str): The tool call identifier for tracking purposes.
#         config (RunnableConfig): Configuration for the runnable environment.

#     Returns:
#         Command: An object containing the transcript and a success message.
#         str: An error message if the transcript is not available.
#     """
#     logger.info(f"Fetching transcript for video link: {video_link}")

#     try:
#         transcript_url = await get_youtube_transcript_url(video_link)
#         if not transcript_url:
#             logger.warning(f"No transcript URL found for video: {video_link}")
#             return f"No transcript URL found. The video may not have subtitles."

#         transcript = await fetch_transcript(transcript_url)
#         if not transcript:
#             logger.warning(f"Transcript is empty for video: {video_link}")
#             return "Transcript is empty."

#         # Log the first 500 characters of the transcript for inspection
#         logger.info(f"Transcript preview for {video_link}: {transcript[:500]}...")

#         return Command(
#             update={
#                 "transcript": transcript,
#                 "messages": [
#                     ToolMessage(
#                         content="Transcript successfully stored in state.",
#                         tool_call_id=tool_call_id,
#                     )
#                 ],
#             }
#         )

#     except Exception as e:
#         logger.error(f"Error fetching transcript for video link {video_link}: {e}")
#         return f"Transcript not available: {e}"


