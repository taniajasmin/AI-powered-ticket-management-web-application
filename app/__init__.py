import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ticket_system.db")
SECRET_KEY = os.getenv("SECRET_KEY", "a-very-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

AI_CLASSIFICATION_ENABLED = os.getenv("AI_CLASSIFICATION_ENABLED", "true").lower() == "true"
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash-lite")
AI_API_URL = os.getenv(
    "AI_API_URL",
    f"https://generativelanguage.googleapis.com/v1beta/models/{AI_MODEL}:generateContent",
)
