# app/controllers/youtube_controller.py
from fastapi import APIRouter, HTTPException
from app.models.state import QueryRequest, SummarizationResponse
from app.services.summarization_service import summarize_video

router = APIRouter(prefix="/api")

@router.post("/summarize", response_model=SummarizationResponse)
async def summarize_endpoint(request: QueryRequest):
    try:
        result = await summarize_video(request.query)
        return SummarizationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
