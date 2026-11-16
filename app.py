"""FastAPI application for Roblox Event Extractor & XP Engine.

Provides web interface and REST API for leaderboard screenshot transcription,
Roblox user and clan verification, and clan event XP computation.
"""

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import FileResponse

import config
from discord_store import DiscordStore
from gemini_vision import GeminiVisionExtractor
from roblox_verifier import RobloxVerifier
from xp_engine import XPEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Application initialization
app = FastAPI(title="Roblox Event Extractor & XP Engine")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core domain service instances
vision_extractor = GeminiVisionExtractor()
roblox_verifier = RobloxVerifier()
xp_engine = XPEngine()
discord_store = DiscordStore()

# Static assets directory
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Pydantic request models
class VerifyUserRequest(BaseModel):
    username: str
    clan_group_id: Optional[int] = None


class CalculateXPRequest(BaseModel):
    events: List[Dict[str, Any]]
    win_xp: Optional[int] = None
    loss_xp: Optional[int] = None


class DiscordMappingPayload(BaseModel):
    username: Optional[str] = None
    discord_id: Optional[str] = None
    mappings: Optional[Dict[str, str]] = None


# Endpoints
@app.get("/")
def read_root():
    """Serves the main web application UI."""
    return FileResponse(static_dir / "index.html")


@app.get("/api/config")
def get_config():
    """Returns runtime configuration and default clan parameters."""
    return {
        "default_clan_name": config.DEFAULT_CLAN_NAME,
        "default_clan_group_id": config.DEFAULT_CLAN_GROUP_ID,
        "win_xp": config.WIN_XP,
        "loss_xp": config.LOSS_XP,
    }


@app.post("/api/extract")
async def extract_leaderboard(
    files: List[UploadFile] = File(...),
    clan_group_id: Optional[int] = Form(None),
):
    """Processes uploaded leaderboard screenshots.

    Transcribes statistics via Gemini Vision and enriches all player records
    with Roblox verification and clan membership data.
    """
    target_group = clan_group_id or config.DEFAULT_CLAN_GROUP_ID
    processed_events = []

    for file in files:
        try:
            image_bytes = await file.read()
            if not image_bytes:
                continue

            event_data = vision_extractor.extract_leaderboard(image_bytes)
            event_data["filename"] = file.filename

            # Collect unique usernames across all teams
            usernames: List[str] = []
            for team in event_data.get("teams", []):
                for player in team.get("players", []):
                    uname = player.get("username")
                    if uname and uname not in usernames:
                        usernames.append(uname)

            # Verify usernames against Roblox API & clan group
            verified_list = roblox_verifier.verify_roster(
                usernames, target_group_id=target_group
            )
            roster_map: Dict[str, Dict[str, Any]] = {}
            for item in verified_list:
                raw_name = item.get("raw")
                if raw_name:
                    roster_map[raw_name] = item
                    roster_map[raw_name.lower()] = item

            # Enrich player entries with verification details
            for team in event_data.get("teams", []):
                for player in team.get("players", []):
                    raw_name = player.get("username", "")
                    v_info = (
                        roster_map.get(raw_name)
                        or roster_map.get(raw_name.lower())
                        or {}
                    )
                    verified_name = v_info.get("verified_name")
                    player["verified_name"] = verified_name
                    player["user_id"] = v_info.get("user_id")
                    player["in_clan"] = v_info.get("in_clan", False)
                    player["clan_role"] = v_info.get("clan_role")
                    player["is_verified"] = v_info.get("is_verified", False)
                    player["discord_id"] = discord_store.get(verified_name) or discord_store.get(raw_name)

            processed_events.append(event_data)
        except Exception as e:
            logger.error(f"Error processing file '{file.filename}': {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process '{file.filename}': {str(e)}",
            )

    return processed_events


@app.post("/api/verify_user")
def verify_user(payload: VerifyUserRequest):
    """Verifies a single Roblox username and checks clan affiliation."""
    target_group = payload.clan_group_id or config.DEFAULT_CLAN_GROUP_ID
    results = roblox_verifier.verify_roster([payload.username], target_group_id=target_group)
    if results:
        return results[0]
    return {
        "raw": payload.username,
        "verified_name": None,
        "user_id": None,
        "in_clan": False,
        "clan_role": None,
        "is_verified": False,
    }


@app.post("/api/calculate_xp")
def calculate_xp(payload: CalculateXPRequest):
    """Calculates attendance, win/loss status, and total XP for verified players."""
    try:
        sig = inspect.signature(xp_engine.calculate_xp)
        kwargs = {}
        if "win_xp" in sig.parameters and payload.win_xp is not None:
            kwargs["win_xp"] = payload.win_xp
        if "loss_xp" in sig.parameters and payload.loss_xp is not None:
            kwargs["loss_xp"] = payload.loss_xp

        return xp_engine.calculate_xp(payload.events, **kwargs)
    except Exception as e:
        logger.error(f"XP calculation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"XP calculation failed: {str(e)}")


@app.get("/api/discord_ids")
def get_discord_ids():
    """Returns stored Roblox-to-Discord ID mappings."""
    return {"mappings": discord_store.get_all()}


@app.post("/api/discord_ids")
def update_discord_ids(payload: DiscordMappingPayload):
    """Updates one or multiple Roblox-to-Discord ID mappings."""
    if payload.mappings is not None:
        discord_store.bulk_set(payload.mappings)
    elif payload.username is not None:
        discord_store.set(payload.username, payload.discord_id)
    return {"status": "ok", "mappings": discord_store.get_all()}


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=config.HOST, port=config.PORT, reload=True)
