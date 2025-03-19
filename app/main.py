# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.controllers.youtube_controller import router as youtube_router

app = FastAPI(title="YouTube Video Summarization API")


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(youtube_router)

# Mount the static files directory
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/")
async def root():
    return {"message": "Welcome to the YouTube Video Summarization API!"}