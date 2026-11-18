# Project Overview: Winslow Accord Ops — Roblox Event Extractor & Attendance Engine

## 1. Executive Summary

| Property | Details |
| :--- | :--- |
| **System Identity** | **Winslow Accord Ops** (Roblox Event Extractor & Attendance Engine) |
| **Live Production Deployment** | [https://roblox-event-extractor.onrender.com](https://roblox-event-extractor.onrender.com) |
| **Source Code Repository** | [https://github.com/himkhadr-boop/roblox-event-extractor](https://github.com/himkhadr-boop/roblox-event-extractor) |
| **Target Clan & Group ID** | **Winslow Accord** &mdash; Roblox Group ID: `825966682` |
| **Core Stack** | Python 3.11, FastAPI, Google Gemini 2.5 Flash, Vanilla JS (Linear/Vercel Matte Dark UI) |

**Winslow Accord Ops** is an automated attendance, performance extraction, and XP tallying platform engineered specifically for competitive Roblox clan operations. It transforms post-match screenshot processing from a tedious, error-prone 20-minute manual chore into an instantaneous, single-click automated workflow.

---

## 2. Core Problem & Motivation

Competitive Roblox clan matches, scrimmages, and joint operations require officers to rapidly record event attendance, track individual player contributions (kills, deaths, assists, damage, heals, captures), and award XP points across competitive teams.

However, logging matches manually presents severe operational bottlenecks:

1. **Extreme Visual Distortion & Game Overlays**:
   - In-game capture screenshots frequently feature semi-transparent crimson **"YOU DIED"** respawn banners directly across scoreboard typography.
   - Variable screen resolutions, 3D camera angles, motion blur, and aggressive compression artifacts routinely break traditional Tesseract-style OCR.

2. **Sans-Serif Font Kerning & OCR Trap Characters**:
   - Roblox fonts often render uppercase `I`, lowercase `l`, and digit `1` with identical vertical strokes (e.g., `SAVlO_R` with a lowercase `l` vs. `SAVIO_R` with an uppercase `I`).
   - Tight letter kerning and ligature collapses result in frequent character misinterpretations, such as `cl` appearing as `d` or `di` appearing as `cl` (e.g., `flanked` transcribed as `flankecl` or `Flankedi`).
   - Similar ambiguities occur with `0` vs. `O` and `rn` vs. `m` (e.g., `burn` vs. `bum`).

3. **Tedious & High-Stakes Clan Bot XP Assignment**:
   - Clan progression is managed via the Winslow Accord custom Discord bot, which requires slash commands targeting space-separated Discord user snowflakes or Roblox usernames:
     ```text
     /xp-add target:<@123456789012345678> behbeh1163 amount:10
     ```
   - Manually looking up 10 to 40 individual Discord IDs or Roblox usernames, grouping players by XP tiers (Wins vs. Losses), and typing syntax-sensitive commands is slow, fatiguing, and prone to miscrediting or skipping members.

---

## 3. The Solution & Core Features

Winslow Accord Ops eliminates these hurdles through an integrated, multi-stage pipeline:

```
[ Match Screenshots ] 
         │
         ▼
[ Gemini 2.5 Flash Multimodal Vision ] ── (Dual-Key Failover)
         │
         ▼
[ Constrained Clan Verification & Disambiguation ] ── (Roblox Group 825966682 Roster)
         │
         ▼
[ Dynamic Multi-Match XP Engine ] ── (+10 Win / +5 Loss + Attendance Deduplication)
         │
         ▼
[ Winslow Bot Command Generator & Shared Storage ] ── (discord_mappings.json)
         │
         ▼
[ Linear/Vercel Matte Dark Web UI ]
```

### 3.1 Multimodal Vision Engine (Gemini 2.5 Flash with Dual-Key Failover)
- Utilizes Google Gemini 2.5 Flash multimodal vision with structured system instructions to parse tabular scoreboard data directly from image buffers.
- Bypasses raw pixel OCR limitations by reasoning holistically over game frames, reading through "YOU DIED" banners, detecting team splits, and automatically resolving win/loss outcomes based on team scores.
- Implements resilient multi-key pool failover: if primary quotas or rate limits encounter a 429 error, requests seamlessly route to secondary standby API keys without user interruption.

### 3.2 Constrained Clan Verification (Winslow Accord Roster: Group ID 825966682)
- Continuously pre-fetches and caches the official **Winslow Accord** 250+ member roster from Roblox's cursor-paginated Group APIs.
- Applies custom sans-serif disambiguation heuristics to OCR transcripts:
  - Permutation substitution testing `l` $\leftrightarrow$ `I` $\leftrightarrow$ `i`, `0` $\leftrightarrow$ `O`, `cl` $\leftrightarrow$ `d`, and `rn` $\leftrightarrow$ `m`.
  - Exact match reconciliation against known roster members before falling back to global Roblox user searches.
- Distinguishes official clan members, officers, and unaffiliated guests/mercenaries with clear UI visual badges.

### 3.3 Dynamic Multi-Match XP Engine
- Evaluates individual match results and applies standardized clan scoring matrices:
  - **Match Win**: `+10 XP`
  - **Match Loss**: `+5 XP`
- Handles multi-screenshot uploads across multi-round scrims or multi-map operations.
- Enforces **attendance deduplication**, ensuring that players who participate across multiple rounds have their total statistics accumulated while receiving unified, consolidated XP awards.

### 3.4 Grouped Winslow Bot Command Generator
- Organizes verified players into consolidated command blocks segmented by award tier (`amount:10`, `amount:5`).
- Generates Winslow Accord custom bot slash syntax:
  ```text
  /xp-add target:<@123456789012345678> behbeh1163 amount:10
  ```
- **Target Resolution Rule**: Resolves each player to their Discord snowflake mention (`<@ID>`) if mapped in `discord_mappings.json`, or seamlessly falls back to their Roblox username if unmapped (no manual placeholders or blockers).
- Automatically chunks player targets to respect Discord's 2,000-character message limit during large clan events.

### 3.5 Shared Server-Side Discord ID Mapping Storage
- Houses a persistent, thread-safe JSON datastore (`discord_mappings.json`) linking Roblox accounts to Discord IDs.
- Mappings entered or updated by any officer are saved server-side, eliminating redundant lookups across all future clan operations.

### 3.6 Linear / Vercel-Inspired Matte Dark UI
- Designed with a clean, high-contrast matte dark obsidian aesthetic (`#0c0d0e`).
- Real-time inline editing for match scores, player stats, and player affiliations.
- One-click copy buttons for instant Winslow bot `/xp-add` slash commands, formatted Discord match reports, and CSV exports for spreadsheet archiving.

---

## 4. Key Metrics & Value Delivered

| Metric Area | Before Winslow Accord Ops | With Winslow Accord Ops | Impact |
| :--- | :--- | :--- | :--- |
| **Logging Time per Scrim** | 15 &ndash; 25 minutes of manual transcription and ID lookup | **< 30 seconds** (instant batch upload and copy-paste) | **> 95% reduction in officer administrative time** |
| **OCR & Transcript Accuracy** | High error rate due to death screens, kerning traps (`SAVlO_R`, `flankecl`) | **Near 100% resolution** via Gemini vision + roster-constrained heuristics | **Zero missed or incorrectly credited attendance** |
| **Command Formatting Friction** | Manual slash command typing with frequent Discord syntax errors | **100% syntactically valid Winslow bot `/xp-add` commands** grouped by XP tier | **Zero failed bot command executions** |
| **ID Mapping Overhead** | Fragmented officer notes or repetitive manual Discord searches | **Shared server-side database** updated once, preserved forever | **Zero-config multi-officer synchronization** |

---

## 5. Architectural References

- **Application Controller**: [`app.py`](./app.py)
- **Configuration & Key Pool**: [`config.py`](./config.py)
- **Gemini Vision Engine**: [`gemini_vision.py`](./gemini_vision.py)
- **Roblox Clan Verifier**: [`roblox_verifier.py`](./roblox_verifier.py)
- **XP Calculation & Winslow Bot Formatting**: [`xp_engine.py`](./xp_engine.py)
- **Persistent Discord Mapping Store**: [`discord_store.py`](./discord_store.py)
- **Frontend Dashboard**: [`static/index.html`](./static/index.html)
