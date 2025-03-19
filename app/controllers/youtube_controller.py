# app/controllers/youtube_controller.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.schemas.state import QueryRequest, SummarizationResponse
from app.services.summarization_service import summarize_video

router = APIRouter(prefix="/api")

@router.post("/summarize", response_model=SummarizationResponse)
async def summarize_endpoint(request: QueryRequest):
    try:
        result = await summarize_video(request.query, request.tts) # type: ignore
        if request.tts and result.get("audio_path"):
            return FileResponse(
                path=result["audio_path"],
                media_type="audio/mpeg",
                filename=result["audio_path"].split("/")[-1]
            )
        return SummarizationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
