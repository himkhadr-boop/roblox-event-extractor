"""Roblox Event Extractor - XP Engine Module.

Calculates player XP, tallies match statistics across events, and formats
leaderboards into Discord text and CSV exports.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    import config
    DEFAULT_WIN_XP = getattr(config, "WIN_XP", 10)
    DEFAULT_LOSS_XP = getattr(config, "LOSS_XP", 5)
except ImportError:
    DEFAULT_WIN_XP = 10
    DEFAULT_LOSS_XP = 5

logger = logging.getLogger(__name__)


def _to_int(val: Any) -> int:
    """Safely converts an arbitrary value to int, defaulting to 0."""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


class XPEngine:
    """
    Computes player XP and aggregates event statistics across Roblox matches.
    Generates leaderboard rankings, Discord-ready text, and CSV output.
    """

    def __init__(self, win_xp: Optional[int] = None, loss_xp: Optional[int] = None) -> None:
        """
        Initializes XPEngine with win and loss XP values.
        Falls back to config settings if values are not provided.
        """
        self.win_xp: int = win_xp if win_xp is not None else DEFAULT_WIN_XP
        self.loss_xp: int = loss_xp if loss_xp is not None else DEFAULT_LOSS_XP

    def calculate_xp(
        self,
        events: List[Dict[str, Any]],
        win_xp: Optional[int] = None,
        loss_xp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculates cumulative XP and match statistics for all players in the provided events.

        Args:
            events: List of event dictionaries, each containing:
                - event_id: str
                - event_name: str
                - is_win: bool
                - players: list of dicts (with username or verified_name, and optional kills, damage, heals, caps)
            win_xp: Optional override for XP awarded on a win.
            loss_xp: Optional override for XP awarded on a loss.

        Returns:
            Dictionary containing:
                - leaderboard: list of player stat dicts sorted by total_xp desc, then username.lower() asc
                - discord_text: formatted string suitable for Discord messages
                - csv_text: formatted CSV string with standard headers
                - clan_labs_commands: formatted Clan Labs /xp slash commands grouped by XP amount
                - summary: total_events, unique_players, total_xp_awarded
        """
        effective_win_xp = win_xp if win_xp is not None else self.win_xp
        effective_loss_xp = loss_xp if loss_xp is not None else self.loss_xp

        player_stats: Dict[str, Dict[str, Any]] = {}

        for event in (events or []):
            event_name = str(event.get("event_name") or "Unnamed Event")
            is_win = bool(event.get("is_win", False))
            award_xp = effective_win_xp if is_win else effective_loss_xp

            players = event.get("players") or []
            seen_in_event: set[str] = set()

            for p in players:
                # Canonical name resolution: prefer verified_name if present
                raw_name = p.get("verified_name") or p.get("username")
                if not raw_name:
                    continue
                username = str(raw_name).strip()
                if not username:
                    continue

                if username not in player_stats:
                    player_stats[username] = {
                        "username": username,
                        "discord_id": None,
                        "clan_role": None,
                        "total_xp": 0,
                        "events_attended": [],
                        "wins": 0,
                        "losses": 0,
                        "total_kills": 0,
                        "total_damage": 0,
                        "total_heals": 0,
                        "total_caps": 0,
                    }

                stat = player_stats[username]

                # Extract optional discord_id and clan_role
                if p.get("discord_id"):
                    stat["discord_id"] = str(p.get("discord_id")).strip()
                if p.get("clan_role"):
                    stat["clan_role"] = str(p.get("clan_role")).strip()

                # Accumulate performance metrics
                stat["total_kills"] += _to_int(p.get("kills"))
                stat["total_damage"] += _to_int(p.get("damage"))
                stat["total_heals"] += _to_int(p.get("heals"))
                stat["total_caps"] += _to_int(p.get("caps"))

                # Award event attendance and XP once per event per player
                if username not in seen_in_event:
                    seen_in_event.add(username)
                    stat["total_xp"] += award_xp
                    stat["events_attended"].append(event_name)
                    if is_win:
                        stat["wins"] += 1
                    else:
                        stat["losses"] += 1

        # Sort leaderboard: total_xp descending, then lowercase username alphabetically
        leaderboard: List[Dict[str, Any]] = sorted(
            player_stats.values(),
            key=lambda p: (-p["total_xp"], p["username"].lower()),
        )

        # Generate Discord plain text
        discord_lines = [f"{p['username']}: {p['total_xp']} XP" for p in leaderboard]
        discord_text = "\n".join(discord_lines)

        # Generate CSV text
        csv_header = "Username,Total_XP,Events_Attended,Wins,Losses,Total_Kills,Total_Damage,Total_Heals,Total_Caps"
        csv_rows = [csv_header]
        for p in leaderboard:
            csv_rows.append(
                f"{p['username']},"
                f"{p['total_xp']},"
                f"{len(p['events_attended'])},"
                f"{p['wins']},"
                f"{p['losses']},"
                f"{p['total_kills']},"
                f"{p['total_damage']},"
                f"{p['total_heals']},"
                f"{p['total_caps']}"
            )
        csv_text = "\n".join(csv_rows)

        # Generate Clan Labs slash commands
        xp_groups: Dict[int, List[str]] = {}
        for p in leaderboard:
            xp = p["total_xp"]
            if xp <= 0:
                continue
            did = p.get("discord_id")
            clean_id = str(did).strip().lstrip("<@!").rstrip(">") if did else ""
            if clean_id:
                mention = f"<@{clean_id}>"
            else:
                mention = f"[MISSING_ID:{p['username']}]"
            xp_groups.setdefault(xp, []).append(mention)

        clan_labs_lines = []
        for amount in sorted(xp_groups.keys(), reverse=True):
            mentions_str = " ".join(xp_groups[amount])
            clan_labs_lines.append(f"/xp users:{mentions_str} action:Add amount:{amount}")
        clan_labs_commands = "\n".join(clan_labs_lines)

        # Summary statistics
        total_xp_awarded = sum(p["total_xp"] for p in leaderboard)
        summary = {
            "total_events": len(events or []),
            "unique_players": len(leaderboard),
            "total_xp_awarded": total_xp_awarded,
        }

        return {
            "leaderboard": leaderboard,
            "discord_text": discord_text,
            "csv_text": csv_text,
            "clan_labs_commands": clan_labs_commands,
            "summary": summary,
        }


if __name__ == "__main__":
    print("Running localized tests for XPEngine...")

    engine = XPEngine(win_xp=10, loss_xp=5)

    dummy_events = [
        {
            "event_id": "evt_001",
            "event_name": "Raid on Frostbite",
            "is_win": True,
            "players": [
                {
                    "username": "bonniebluesbeast",
                    "verified_name": "bonniebluesbeast",
                    "kills": 15,
                    "damage": 1200,
                    "heals": 50,
                    "caps": 3,
                },
                {
                    "username": "flankecl",
                    "verified_name": "flankecl",
                    "kills": 8,
                    "damage": 750,
                    "heals": 20,
                    "caps": 1,
                },
                {
                    "username": "unverified_warrior",
                    "kills": 5,
                    "damage": 400,
                    "heals": 0,
                    "caps": 0,
                },
            ],
        },
        {
            "event_id": "evt_002",
            "event_name": "Defense of Outpost",
            "is_win": False,
            "players": [
                {
                    "username": "bonniebluesbeast",
                    "verified_name": "bonniebluesbeast",
                    "kills": 10,
                    "damage": 800,
                    "heals": 30,
                    "caps": 1,
                },
                {
                    "username": "albatross",
                    "verified_name": "Albatross",
                    "kills": 12,
                    "damage": 950,
                    "heals": 0,
                    "caps": 2,
                },
            ],
        },
    ]

    result = engine.calculate_xp(dummy_events)

    # 1. Verify summary
    summary = result["summary"]
    assert summary["total_events"] == 2, f"Expected 2 events, got {summary['total_events']}"
    assert summary["unique_players"] == 4, f"Expected 4 players, got {summary['unique_players']}"
    assert summary["total_xp_awarded"] == 40, f"Expected 40 XP, got {summary['total_xp_awarded']}"

    # 2. Verify leaderboard ordering (bonnie: 15, flankecl: 10, unverified: 10, Albatross: 5)
    lb = result["leaderboard"]
    assert len(lb) == 4, f"Expected 4 leaderboard entries, got {len(lb)}"
    assert lb[0]["username"] == "bonniebluesbeast" and lb[0]["total_xp"] == 15
    assert lb[1]["username"] == "flankecl" and lb[1]["total_xp"] == 10
    assert lb[2]["username"] == "unverified_warrior" and lb[2]["total_xp"] == 10
    assert lb[3]["username"] == "Albatross" and lb[3]["total_xp"] == 5

    # 3. Verify stats aggregation
    bonnie = lb[0]
    assert bonnie["wins"] == 1 and bonnie["losses"] == 1
    assert bonnie["events_attended"] == ["Raid on Frostbite", "Defense of Outpost"]
    assert bonnie["total_kills"] == 25
    assert bonnie["total_damage"] == 2000
    assert bonnie["total_heals"] == 80
    assert bonnie["total_caps"] == 4

    # 4. Verify discord_text format
    expected_discord = (
        "bonniebluesbeast: 15 XP\n"
        "flankecl: 10 XP\n"
        "unverified_warrior: 10 XP\n"
        "Albatross: 5 XP"
    )
    assert result["discord_text"] == expected_discord, f"Unexpected discord_text:\n{result['discord_text']}"

    # 5. Verify csv_text format
    csv_lines = result["csv_text"].split("\n")
    assert csv_lines[0] == "Username,Total_XP,Events_Attended,Wins,Losses,Total_Kills,Total_Damage,Total_Heals,Total_Caps"
    assert csv_lines[1] == "bonniebluesbeast,15,2,1,1,25,2000,80,4"
    assert csv_lines[2] == "flankecl,10,1,1,0,8,750,20,1"
    assert csv_lines[3] == "unverified_warrior,10,1,1,0,5,400,0,0"
    assert csv_lines[4] == "Albatross,5,1,0,1,12,950,0,2"

    # Clan Labs command check on dummy_events (with missing IDs)
    expected_clan_labs = (
        "/xp users:[MISSING_ID:bonniebluesbeast] action:Add amount:15\n"
        "/xp users:[MISSING_ID:flankecl] [MISSING_ID:unverified_warrior] action:Add amount:10\n"
        "/xp users:[MISSING_ID:Albatross] action:Add amount:5"
    )
    assert result["clan_labs_commands"] == expected_clan_labs, f"Unexpected clan_labs_commands:\n{result['clan_labs_commands']}"

    # 6. Verify duplicate player in single event handling
    dup_event = [
        {
            "event_id": "evt_dup",
            "event_name": "Duplicate Test",
            "is_win": True,
            "players": [
                {"username": "clone_trooper", "kills": 5, "damage": 100},
                {"username": "clone_trooper", "kills": 3, "damage": 50},
            ],
        }
    ]
    dup_res = engine.calculate_xp(dup_event)
    dup_player = dup_res["leaderboard"][0]
    assert dup_player["total_xp"] == 10, f"Expected 10 XP, got {dup_player['total_xp']}"
    assert dup_player["total_kills"] == 8, f"Expected 8 kills, got {dup_player['total_kills']}"
    assert dup_player["total_damage"] == 150, f"Expected 150 damage, got {dup_player['total_damage']}"
    assert len(dup_player["events_attended"]) == 1

    # 7. Verify empty events handling
    empty_res = engine.calculate_xp([])
    assert empty_res["leaderboard"] == []
    assert empty_res["discord_text"] == ""
    assert empty_res["csv_text"] == "Username,Total_XP,Events_Attended,Wins,Losses,Total_Kills,Total_Damage,Total_Heals,Total_Caps"
    assert empty_res["clan_labs_commands"] == ""
    assert empty_res["summary"] == {"total_events": 0, "unique_players": 0, "total_xp_awarded": 0}

    # 8. Verify Clan Labs slash commands with Discord IDs and roles
    clan_events = [
        {
            "event_id": "evt_clan",
            "event_name": "Clan Scrim",
            "is_win": True,
            "players": [
                {
                    "username": "Player1",
                    "discord_id": "111",
                    "clan_role": "Officer",
                },
                {
                    "username": "Player2",
                    "discord_id": "<@222>",
                    "clan_role": "Member",
                },
            ],
        }
    ]
    clan_res = engine.calculate_xp(clan_events)
    assert clan_res["clan_labs_commands"] == "/xp users:<@111> <@222> action:Add amount:10"
    assert clan_res["leaderboard"][0]["discord_id"] == "111"
    assert clan_res["leaderboard"][0]["clan_role"] == "Officer"
    assert clan_res["leaderboard"][1]["discord_id"] == "<@222>"
    assert clan_res["leaderboard"][1]["clan_role"] == "Member"

    print("All localized tests passed successfully!")
