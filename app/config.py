# app/config.py
from decouple import config
from dotenv import load_dotenv

load_dotenv()

SERPAPI_API_KEY = config("SERPAPI_API_KEY")
GROQ_API_KEY = config("GROQ_API_KEY")
TOGETHER_API_KEY = config("TOGETHER_API_KEY")
MODEL_NAME = "llama-3.3-70b-versatile"
