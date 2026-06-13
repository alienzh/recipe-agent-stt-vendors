# Agora Conversational AI — STT Vendors Recipe (Python)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![Bun](https://img.shields.io/badge/bun-latest-black)](https://bun.sh/)

The **STT vendors** recipe in the Agora Conversational AI recipes family.
A voice assistant whose **STT leg is a data-driven switchboard** over every
A4.1 STT vendor. It **runs zero-key on the default `deepgram` STT** (Agora-managed,
no key required); set `STT_VENDOR=<x>` plus that vendor's key to swap in any other
transcriber. The LLM and TTS legs stay on the proven keyless configs, so only the
transcription leg changes.

**Pipeline:** **`<STT_VENDOR>`** (default `deepgram`, keyless) → `OpenAI(gpt-4o-mini)` → `MiniMaxTTS`

## Vendors

Pick a vendor with `STT_VENDOR`; supply the required env vars; optionally override
the model with `STT_MODEL` (vendors with a model field).

| Vendor | `STT_VENDOR` | Required env | Default model / language |
| --- | --- | --- | --- |
| Deepgram (managed) | `deepgram` 🟢 | _none_ | `nova-3`, `en` |
| Ares (managed) | `ares` 🟢 | _none_ | SDK default |
| AssemblyAI | `assemblyai` | `ASSEMBLYAI_API_KEY` | `en` |
| Speechmatics | `speechmatics` | `SPEECHMATICS_API_KEY` | `en` |
| OpenAI | `openai` | `OPENAI_STT_API_KEY` | `gpt-4o-transcribe`, `en` |
| Microsoft Azure | `microsoft` | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | `en-US` |
| Google | `google` | `GOOGLE_APPLICATION_CREDENTIALS_JSON`, `GOOGLE_PROJECT_ID`, `GOOGLE_LOCATION` | `en-US` |
| Amazon Transcribe | `amazon` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | `en-US` |
| Sarvam | `sarvam` | `SARVAM_API_KEY` | `en-IN` |

🟢 = keyless default. The selected vendor's credentials are validated **when the
agent starts** (not at construction), so `/get_config` always works key-less.

## Prerequisites

- [Python 3.10+](https://www.python.org/)
- [Bun](https://bun.sh/)
- [Agora CLI](https://github.com/AgoraIO/cli) — makes generating an App ID + App Certificate easy

## Run It

```bash
# 1. Install web deps + create the Python venv
bun run setup

# 2. Add Agora credentials (CLI), or edit server/.env.local by hand
agora login
agora project use <your-project>          # select which project to use
agora project env write server/.env.local # writes App ID + Certificate

# 3. Run backend + web
bun run dev
```

Open [http://localhost:3000](http://localhost:3000) → **Start Conversation** → speak.
Watch the **Event Timeline** panel update in real time.

To try a different STT vendor, set `STT_VENDOR` and that vendor's key in
`server/.env.local` (see [Vendors](#vendors)), then restart.

### Working from a clone

`bun run setup` creates the Python venv and installs web dependencies.
`bun run dev` brings up both services. You still need Agora credentials in
`server/.env.local` before a conversation can connect.

Services:

- Frontend — http://localhost:3000
- Backend — http://localhost:8000
- API docs — http://localhost:8000/docs

## Deploy

Deploy `web` (Next.js) and `server` (a reachable FastAPI backend). Set
`AGENT_BACKEND_URL` in the web deployment so the Next rewrites reach the backend.

A backend-only Docker image is published to
`ghcr.io/AgoraIO-Conversational-AI/recipe-agent-stt-vendors` on `v*` tags.
It exposes **BACKEND-ONLY** (:8000). On the default `deepgram` vendor no extra
credentials are needed — Deepgram STT is Agora-managed.

## Environment variables

| Variable | Required | Default | Notes |
| --- | :---: | :---: | --- |
| `AGORA_APP_ID` | ✅ | — | Agora Console → Project → App ID |
| `AGORA_APP_CERTIFICATE` | ✅ | — | Agora Console → Project → App Certificate |
| `STT_VENDOR` | | `deepgram` | Which STT vendor to use (see [Vendors](#vendors)) |
| `STT_MODEL` | | per-vendor | Optional model override (vendors with a model field) |
| `STT_LANGUAGE` | | per-vendor | Optional language hint (documented per vendor) |
| `AGENT_GREETING` | | built-in | Optional opening line override |
| _vendor creds_ | | — | Required only for the selected BYO vendor (see [Vendors](#vendors)) |

## Commands

```bash
bun run setup            # install web deps + create server/ venv
bun run dev              # run backend (:8000) + web (:3000)

bun run doctor           # prerequisite check (no creds needed)
bun run doctor:local     # + .env.local + credentials checks

bun run verify           # web-only gate (no Agora creds needed)
bun run verify:local     # full local gate: backend compile + smoke tests + web build
bun run clean            # remove venvs and build artifacts
```

Tests run standalone (no Agora cloud needed): `pytest` in `server/`, plus
`bun run verify` in `web/`. CI runs them on Linux/macOS/Windows × Python 3.10 & 3.13.

## Architecture

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js  ──rewrite──▶  Agent backend  (server/, localhost:8000)
                          │  starts agent session
                          │  STT leg = build_vendor(STT_VENDOR)
                          │  flags: enable_rtm=true, enable_metrics=true,
                          │         enable_error_message=true
                          ▼
                       Agora ConvoAI Cloud
                          │  <STT_VENDOR> (default Deepgram, keyless)
                          │  OpenAI gpt-4o-mini (managed)
                          │  MiniMax TTS (managed)
                          │  RTM events → browser
                          ▼
                       EventTimeline + annotated transcript in the web UI
```

The STT vendor switchboard lives in `server/src/vendors.py` — a data-driven
registry mapping each vendor to `{cls, creds, defaults}`. See
[ARCHITECTURE.md](./ARCHITECTURE.md).

## What You Get

- A **vendor switchboard** for the STT leg: one `build_vendor()` over a `SPECS`
  table covering all nine A4.1 STT vendors, selected via `STT_VENDOR`.
- A **Next.js** web client (:3000) with a live **EventTimeline** (state, metric,
  error, turn events; reverse-chronological, capped at 50) and an **annotated
  transcript** that shows the current agent state in the header.
- A **FastAPI** agent backend (:8000) that owns Agora token generation and the
  agent session lifecycle.
- **Zero-key by default** — the full pipeline runs with no STT API key on the
  managed `deepgram` vendor.

## How It Works

1. The browser calls `/api/get_config`; the backend mints an Agora token. This
   works key-less even when a BYO `STT_VENDOR` is selected — credentials are only
   checked at agent start.
2. The browser joins the RTC channel, then calls `/api/startAgent`; the backend
   builds the selected STT via `build_vendor(STT_VENDOR)` (raising a clear error
   if a BYO vendor is missing its credentials) and starts the agent with
   `data_channel="rtm"`, `enable_metrics=True`, and `enable_error_message=True`.
3. The agent speaks with the user. Agora emits RTM events for every state change,
   per-stage metric, transcript turn, and error.
4. The web client's `AgoraVoiceAI` SDK receives these events and appends a
   `TimelineEvent` for each one (capped at 50).
5. `EventTimeline` renders the events in reverse-chronological order with a
   colored badge per kind. The transcript header shows the current agent state.
6. `/api/stopAgent` ends the session.

## Repo Map

- `web/` — Next.js frontend (:3000); RTC/RTM lifecycle, EventTimeline, transcript.
- `server/` — FastAPI agent backend (:8000); Agora tokens + agent lifecycle.
- `server/src/vendors.py` — the data-driven STT vendor registry.
- `ARCHITECTURE.md` — system shape and component boundaries.
- `AGENTS.md` — guide for coding agents working in this repo.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `STT vendor '<x>' requires environment variable(s): ...` at start | Set the listed env vars for that `STT_VENDOR` (see [Vendors](#vendors)), or switch back to `deepgram`. |
| No events appear in the timeline | Ensure `enable_rtm`, `enable_metrics`, `enable_error_message` are set (they are, by default in this recipe). |
| Local calls fail under a global proxy (Clash, etc.) | Configure your proxy to send `127.0.0.1`, `localhost`, and RFC-1918 ranges DIRECT. |

## More Docs

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [AGENTS.md](./AGENTS.md)

## License

Released under the [MIT License](./LICENSE).
