"""Gemini Vision Extractor for Roblox Leaderboard Screenshots.

Extracts structured player and team statistics from screenshot images using Google's
gemini-2.5-flash model with structured JSON response schema enforcement.
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LEADERBOARD_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "match_title": {"type": "STRING"},
        "teams": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "team_name": {"type": "STRING"},
                    "score": {"type": "STRING"},
                    "players": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "username": {"type": "STRING"},
                                "kills": {"type": "INTEGER"},
                                "damage": {"type": "INTEGER"},
                                "heals": {"type": "INTEGER"},
                                "caps": {"type": "INTEGER"},
                                "score": {"type": "INTEGER"},
                            },
                            "required": ["username"],
                        },
                    },
                },
                "required": ["team_name", "players"],
            },
        },
    },
    "required": ["teams"],
}

EXTRACTION_PROMPT = (
    "Accurately transcribe all player usernames from this Roblox leaderboard/scoreboard screenshot.\n"
    "Guidelines:\n"
    "1. Accurately transcribe all player usernames from Roblox leaderboard/scoreboard screenshot.\n"
    "2. Separate players by team (e.g. Raiders, Snow Core, Winslow Accord, Hostiles).\n"
    "3. Capture stats if visible (kills, damage, heals, caps, score).\n"
    "4. Ignore any transient overlays like 'YOU DIED' death screen banner and focus on reading the underlying table rows."
)


class GeminiVisionExtractor:
    """Manages Gemini vision extraction calls with round-robin key rotation and failover."""

    def __init__(self, api_keys: Optional[List[str]] = None):
        """Initialize with optional list of API keys. Defaults to GEMINI_API_KEYS from config."""
        if api_keys is not None:
            self.api_keys = [k for k in api_keys if k]
        else:
            try:
                from config import GEMINI_API_KEYS
                self.api_keys = [k for k in GEMINI_API_KEYS if k]
            except (ImportError, AttributeError):
                self.api_keys = []

        self._current_key_idx = 0

    @staticmethod
    def _detect_mime_type(image_bytes: bytes) -> str:
        """Infer image MIME type from magic headers."""
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if image_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if image_bytes.startswith(b"RIFF") and len(image_bytes) >= 12 and image_bytes[8:12] == b"WEBP":
            return "image/webp"
        return "image/png"

    @staticmethod
    def _parse_gemini_response(res_json: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and parse structured JSON from Gemini response candidates."""
        candidates = res_json.get("candidates", [])
        if not candidates:
            raise ValueError(f"No candidates returned from Gemini API: {res_json}")

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise ValueError(f"No content parts in Gemini API response: {candidates[0]}")

        text = parts[0].get("text", "").strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        return json.loads(text)

    def extract_leaderboard(self, image_bytes: bytes) -> Dict[str, Any]:
        """Transcribe Roblox leaderboard from image bytes using gemini-2.5-flash with key failover."""
        if not self.api_keys:
            raise ValueError("No Gemini API keys available. Provide api_keys or set GEMINI_API_KEYS in config.py.")

        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = self._detect_mime_type(image_bytes)

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": EXTRACTION_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_data,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_schema": LEADERBOARD_RESPONSE_SCHEMA,
            },
        }

        req_data = json.dumps(payload).encode("utf-8")
        num_keys = len(self.api_keys)
        max_attempts = max(2, num_keys)
        last_error: Optional[Exception] = None

        for attempt in range(max_attempts):
            key = self.api_keys[self._current_key_idx % num_keys]
            self._current_key_idx = (self._current_key_idx + 1) % num_keys

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    resp_bytes = resp.read()
                    resp_text = resp_bytes.decode("utf-8")
                    res_json = json.loads(resp_text)
                    return self._parse_gemini_response(res_json)
            except urllib.error.HTTPError as e:
                last_error = e
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
                logger.warning(
                    "Gemini API HTTP %s (attempt %d/%d): %s",
                    e.code,
                    attempt + 1,
                    max_attempts,
                    err_body,
                )
                continue
            except Exception as e:
                last_error = e
                logger.warning(
                    "Gemini API request failed (attempt %d/%d): %s",
                    attempt + 1,
                    max_attempts,
                    e,
                )
                continue

        raise RuntimeError(f"Failed to extract leaderboard after {max_attempts} attempts: {last_error}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Verifying GeminiVisionExtractor...")

    # Verification 1: Instantiation with explicit keys and key rotation
    mock_keys = ["mock_key_alpha", "mock_key_beta"]
    extractor = GeminiVisionExtractor(api_keys=mock_keys)
    assert len(extractor.api_keys) == 2, "Failed to store provided API keys"

    first_key = extractor.api_keys[extractor._current_key_idx % len(extractor.api_keys)]
    extractor._current_key_idx = (extractor._current_key_idx + 1) % len(extractor.api_keys)
    second_key = extractor.api_keys[extractor._current_key_idx % len(extractor.api_keys)]
    assert first_key != second_key, "Key rotation check failed"

    # Verification 2: MIME type detection
    assert extractor._detect_mime_type(b"\x89PNG\r\n\x1a\n...") == "image/png"
    assert extractor._detect_mime_type(b"\xff\xd8\xff...") == "image/jpeg"

    # Verification 3: Mock response parsing
    mock_gemini_resp = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "match_title": "Raid on Outpost",
                                "teams": [
                                    {
                                        "team_name": "Snow Core",
                                        "score": "500",
                                        "players": [
                                            {"username": "Player1", "kills": 15, "score": 1500}
                                        ]
                                    }
                                ]
                            })
                        }
                    ]
                }
            }
        ]
    }
    parsed = extractor._parse_gemini_response(mock_gemini_resp)
    assert parsed["match_title"] == "Raid on Outpost"
    assert len(parsed["teams"]) == 1
    assert parsed["teams"][0]["players"][0]["username"] == "Player1"

    # Verification 4: Default instantiation (handles missing config gracefully)
    extractor_default = GeminiVisionExtractor()
    print(f"Default extractor instantiated with {len(extractor_default.api_keys)} keys.")

    print("All localized checks passed successfully!")
