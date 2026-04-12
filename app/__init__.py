import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is missing. Please add your Neon Postgres URL to your .env file!")

# Ensure URLs from providers like Neon use the asyncpg driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

if "postgresql+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("sslmode=", "ssl=")
    if "&channel_binding=" in DATABASE_URL:
        # Strip out channel_binding entirely as asyncpg does not support it
        DATABASE_URL = DATABASE_URL.split("&channel_binding=")[0]
    elif "?channel_binding=" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?channel_binding=")[0]


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
