# AGENTS.md — Winslow Accord Ops: Roblox Event Extractor

> Operational handbook, architectural invariants, design guidelines, and development directives for autonomous agents and contributors.

---

## 1. Project Overview & Scope

- **Project Name**: Roblox Event Extractor (Winslow Accord Ops)
- **Repository**: [https://github.com/himkhadr-boop/roblox-event-extractor](https://github.com/himkhadr-boop/roblox-event-extractor)
- **Live Production URL**: [https://roblox-event-extractor.onrender.com](https://roblox-event-extractor.onrender.com)
- **Core Mission**:
  Automate post-match reporting and clan administration for Winslow Accord Roblox competitive events:
  1. **Scoreboard Ingestion**: Upload match screenshots (end-game scoreboards, round recaps).
  2. **OCR Transcription**: Extract tabular player names, scores, kills, deaths, and team placements using Google Gemini 2.5 Flash.
  3. **Roster Verification**: Verify player membership against the official Winslow Accord Roblox group.
  4. **XP Accumulation**: Aggregate points across multiple matches or rounds with win/loss multipliers and manual adjustments.
  5. **Discord Identity Mapping**: Persist and associate Roblox usernames with Discord snowflake IDs.
  6. **Winslow Bot Dispatch**: Format aggregated XP gains directly into copy-pasteable Winslow Accord custom bot slash commands (`/xp-add`).

---

## 2. Architectural Invariants & Constants

All agents and contributors must preserve the following system invariants:

| Parameter | Value | Location / Notes |
| :--- | :--- | :--- |
| **Winslow Accord Group ID** | `825966682` | `config.py` (`DEFAULT_CLAN_GROUP_ID`), `roblox_verifier.py` |
| **Win XP Award** | `10 XP` | `config.py` (`WIN_XP`), `xp_engine.py` |
| **Loss XP Award** | `5 XP` | `config.py` (`LOSS_XP`), `xp_engine.py` |
| **Gemini Model** | `gemini-2.5-flash` | `gemini_vision.py` |
| **Dual Gemini API Keys** | Comma-separated | Automatic failover & round-robin fallback on HTTP 429 / quota limit |
| **Discord Store Path** | `discord_mappings.json` | Server-side, thread-safe read/write via `discord_store.py` (`threading.Lock`) |
| **Winslow Bot Command Format** | `/xp-add target:<@ID1> <RobloxUser2> amount:X` | Valid Winslow Accord bot slash syntax; targets Discord mention (`<@ID>`) if mapped, or Roblox username if unmapped. Multi-target space-separated |

### Winslow Bot Command Syntax Standard (`/xp-add`)
Winslow Accord's custom bot uses the `/xp-add` command syntax with space-separated targets:
```text
/xp-add target:<@123456789012345678> behbeh1163 amount:10
```
- **Target Resolution Rule**: For each player, use their Discord snowflake mention (`<@ID>`) if mapped, or seamlessly fall back to their Roblox username if unmapped (no blocking or manual placeholders).
- Respect Discord's 2000-character message limit by auto-chunking command batches if player counts are large.

---

## 3. Tech Stack & Directory Structure

```text
roblox-event-extractor/
├── app.py                  # FastAPI application entry point, REST endpoints, static file serving
├── config.py               # Central environment variable loading (.env) and configuration constants
├── gemini_vision.py        # Gemini 2.5 Flash vision client, structured OCR prompt, key failover
├── roblox_verifier.py      # Roblox Open Cloud / Web API group verification with TTL caching
├── xp_engine.py            # Event aggregation, win/loss math, Winslow bot slash syntax formatting
├── discord_store.py        # Thread-safe persistent JSON storage for Roblox <-> Discord mappings
├── discord_mappings.json   # Persistent key-value store ({ "RobloxUsernameLower": "DiscordSnowflake" })
├── static/                 # Frontend assets (Vanilla HTML5 / Modern CSS / ES6 JavaScript)
│   ├── index.html          # SPA single-page interface
│   ├── styles.css          # Matte dark design system
│   └── app.js              # State management, image upload, OCR trigger, interactive review
├── requirements.txt        # Production Python dependencies
├── render.yaml             # Render.com Blueprint configuration
├── Procfile                # Web process definition for PaaS deployment
└── AGENTS.md               # Agent guidelines and architectural rules (this document)
```

---

## 4. Design & UI Guidelines

The interface adheres to an operational, matte-dark aesthetic inspired by **Linear** and **Vercel**:

1. **Color Palette**:
   - Background Canvas: `#0B0D0E` (deep matte neutral, not pure black)
   - Surface / Panels: `#121517` with subtle `#181B1E` elevation
   - Borders: Hairline 1px borders using `#262A2E` or `#2E3338`
   - Accent & Highlights: Muted tactical amber/slate (`#D4A373`, `#4F5D75`) or subtle desaturated emerald for verified status
   - Text Hierarchy: Primary `#EDEFF2`, Secondary `#8A9099`, Muted `#585E66`

2. **Design Prohibitions**:
   - **Zero AI Buzzwords**: Never use terms like *"AI-Powered"*, *"Magical"*, *"Next-Gen Neural OCR"*, or *"Smart Scanner"*. Frame features as tactical data extraction tools (*"Scoreboard Ingestion"*, *"OCR Transcription"*, *"Roster Validation"*).
   - **Zero Neon Aesthetics**: No saturated purple/cyan neon gradients, no glowing radial drop-shadows (`box-shadow: 0 0 25px #00ffcc`), and no animated floating gradient cards.
   - **Zero Clutter**: Functional spacing (4px / 8px baseline grid), dense informative data tables, and minimal cognitive friction.

---

## 5. Execution & Development Guidelines

### Shell Environment
- **Platform**: Windows PowerShell 5.
- **Rule**: **NEVER** use `&&` to chain commands (PowerShell 5 does not support POSIX `&&`). Run sequential commands as separate commands or separate with `;`.

### Local Execution
To run the server locally:
```powershell
py -m uvicorn app:app --host 127.0.0.1 --port 8000
```
Then navigate to: `http://127.0.0.1:8000`

### Automated Deployment
- The repository is connected to Render.com via Blueprint (`render.yaml`).
- **Rule**: Pushing any commit to `origin main` automatically initiates a deployment to the live service at `https://roblox-event-extractor.onrender.com`.
- Always verify changes locally before pushing to `origin main`.

---

## 6. Subagent Rules of Engagement

1. **Strict Single-File Scope**: When assigned a task, touch only the designated target file. Do not perform speculative edits in surrounding files.
2. **Surgical Precision**: Preserve existing logic, comments, and structure. Avoid replacing entire files when localized diffs suffice.
3. **No Workspace-Wide Locks in Parallel**: Never run global package installs, long daemon loops, or full rebuilds during parallel Builder execution.
4. **Anti-Accretion Directive**: Write clean, concise code. Strip unused imports and dead branches rather than layering defensive wrappers.
5. **Circuit Breaker**: If verification fails 3 consecutive times, stop immediately, report exact output and `git diff`, and wait for instructions.
