import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the project directory
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Environment variables & configuration
_raw_keys = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS: list[str] = [k.strip() for k in _raw_keys.split(",") if k.strip()]

DEFAULT_CLAN_NAME: str = os.getenv("DEFAULT_CLAN_NAME", "Winslow Accord")
DEFAULT_CLAN_GROUP_ID: int = int(os.getenv("DEFAULT_CLAN_GROUP_ID", "825966682"))
WIN_XP: int = int(os.getenv("WIN_XP", "10"))
LOSS_XP: int = int(os.getenv("LOSS_XP", "5"))
PORT: int = int(os.getenv("PORT", "8000"))
HOST: str = os.getenv("HOST", "127.0.0.1")

if __name__ == "__main__":
    print("Configuration loaded successfully:")
    print(f"  GEMINI_API_KEYS count: {len(GEMINI_API_KEYS)}")
    print(f"  DEFAULT_CLAN_NAME: {DEFAULT_CLAN_NAME}")
    print(f"  DEFAULT_CLAN_GROUP_ID: {DEFAULT_CLAN_GROUP_ID}")
    print(f"  WIN_XP: {WIN_XP}")
    print(f"  LOSS_XP: {LOSS_XP}")
    print(f"  PORT: {PORT}")
    print(f"  HOST: {HOST}")
