# app/services/tts_service.py
from gtts import gTTS
import os
import uuid

AUDIO_DIR = "assets/audio"

def text_to_speech(text: str) -> str:
    os.makedirs(AUDIO_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    tts = gTTS(text)
    tts.save(filepath)
    return filepath
