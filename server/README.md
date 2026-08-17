# Agora Agent Backend — STT Vendors Recipe

FastAPI service that owns Agora token generation and agent session lifecycle for
the STT vendors recipe. It is the service the web client reaches through the
Next.js `/api/*` rewrite proxy (port 8000).

## What this service does

Starts a conversational AI agent whose **STT leg is selected at runtime** from a
data-driven registry (`src/vendors.py`), while keeping the LLM and TTS legs on the
proven keyless configs. It also enables the three flags that drive the web event
surface:

- `data_channel = "rtm"` — routes all events over RTM to the browser
- `enable_metrics = True` — emits per-stage latency (STT, LLM, TTS)
- `enable_error_message = True` — surfaces agent and message errors over RTM

**Pipeline:** `<STT_VENDOR>` (default `deepgram`, Agora-managed, keyless) → `OpenAI(gpt-4o-mini)` → `MiniMaxTTS`

The default `deepgram` vendor is Agora-managed (keyless), so the recipe is
**zero-key** out of the box. There is **no separate `llm/` service**.

## The vendor registry

`src/vendors.py` is a data-driven switchboard:

- `SPECS` maps each `STT_VENDOR` value to `VendorSpec(cls, creds, defaults, model_field)`.
- `build_vendor(name, env)` builds the vendor, raising `ValueError` listing any
  missing credential env vars.
- The UI can send optional Ares keywords with `startAgent`; the backend sends
  them as `params.keywords`.
- `required_env(name)` / `available()` expose the registry.

`agent.py` reads `STT_VENDOR` in `__init__` (no validation) and calls
`build_vendor(self.vendor)` in `start()` — so BYO credentials are validated only
when a conversation starts, and `/get_config` stays key-less.

## Run

Use the repo-root `README.md` for the full local flow (`bun run dev`). To work on
this module directly:

The root commands below select the correct virtualenv interpreter on macOS,
Linux, and Windows, so activation is not required:

```shell
bun run setup:server
bun run backend
```

## Environment

Required:

- `AGORA_APP_ID` — Agora project App ID.
- `AGORA_APP_CERTIFICATE` — Agora project App Certificate.

Optional:

| Variable | Default | Notes |
| --- | :---: | --- |
| `STT_VENDOR` | `deepgram` | Which STT vendor to build (see the root README Vendors table) |
| `STT_MODEL` | per-vendor | Optional model override (vendors with a model field) |
| `STT_LANGUAGE` | per-vendor | Optional language hint (documented per vendor) |
| `AGENT_GREETING` | built-in | Optional opening line override |

Selecting a BYO `STT_VENDOR` additionally requires that vendor's credential env
vars (see `required_env` in `src/vendors.py` and the root README). These are
validated when the agent starts, not at construction.

## API

- `GET /get_config` — token + channel/UID config
- `POST /startAgent` — start an agent session (builds the selected STT)
- `POST /stopAgent` — stop an agent session

The repo-root `bun run verify:local:fastapi` exercises these routes through the
Next proxy using a fake agent (`scripts/run_fake_server.py`), so no live Agora
session is required.
