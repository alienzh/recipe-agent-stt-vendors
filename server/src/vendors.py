"""STT vendor registry — one readable builder per Agora-supported STT vendor.

Each `build_<vendor>(env)` is a self-contained, copy-pasteable example of wiring
that vendor into an Agora Conversational AI agent: it shows the real SDK
constructor call and exactly which env vars it needs. `build_vendor(name)`
selects one by `STT_VENDOR`. Optional `STT_MODEL` overrides the model on
vendors that expose a model field.

Add or change a vendor by editing its builder below + the REGISTRY line.
"""
import os
from typing import Callable, Dict, List, Optional, Tuple

from agora_agent.agentkit.vendors import (
    DeepgramSTT, AresSTT, AssemblyAISTT, SpeechmaticsSTT, OpenAISTT,
    MicrosoftSTT, GoogleSTT, AmazonSTT, SarvamSTT,
)
from agora_agent.agentkit.preview import GeminiSTT, GeminiSTTModels

CATEGORY = "STT"


def _model(env, default: str) -> str:
    """The selected model, overridable with STT_MODEL."""
    return env.get("STT_MODEL") or default


# --- one builder per vendor (these are the samples) -------------------------

def build_deepgram(env):
    """Deepgram — Agora-managed, key-less by default."""
    return DeepgramSTT(model=_model(env, "nova-3"), language="en")


def build_ares(env, keywords: Optional[List[str]] = None):
    """Ares — Agora-managed, with optional request-level keywords."""
    return AresSTT(keywords=keywords)


def build_assemblyai(env):
    """AssemblyAI — set ASSEMBLYAI_API_KEY (assemblyai.com)."""
    return AssemblyAISTT(
        api_key=env["ASSEMBLYAI_API_KEY"],
        language="en",
    )


def build_speechmatics(env):
    """Speechmatics — set SPEECHMATICS_API_KEY (speechmatics.com)."""
    return SpeechmaticsSTT(
        api_key=env["SPEECHMATICS_API_KEY"],
        language="en",
    )


def build_openai(env):
    """OpenAI transcription — set OPENAI_STT_API_KEY (platform.openai.com)."""
    return OpenAISTT(
        api_key=env["OPENAI_STT_API_KEY"],
        model=_model(env, "gpt-4o-transcribe"),
        prompt="Transcribe the audio.",
        language="en",
    )


def build_microsoft(env):
    """Microsoft Azure Speech — set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION."""
    return MicrosoftSTT(
        key=env["AZURE_SPEECH_KEY"],
        region=env["AZURE_SPEECH_REGION"],
        language="en-US",
    )


def build_google(env):
    """Google Cloud Speech — set GOOGLE_APPLICATION_CREDENTIALS_JSON, GOOGLE_PROJECT_ID, GOOGLE_LOCATION."""
    return GoogleSTT(
        adc_credentials_string=env["GOOGLE_APPLICATION_CREDENTIALS_JSON"],
        project_id=env["GOOGLE_PROJECT_ID"],
        location=env["GOOGLE_LOCATION"],
        language="en-US",
    )


def build_gemini(env):
    """Gemini transcription preview — set GEMINI_STT_API_KEY."""
    return GeminiSTT(
        api_key=env["GEMINI_STT_API_KEY"],
        model=_model(env, GeminiSTTModels.TRANSCRIBE_35_LIVE),
    )


def build_amazon(env):
    """Amazon Transcribe — set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION."""
    return AmazonSTT(
        access_key=env["AWS_ACCESS_KEY_ID"],
        secret_key=env["AWS_SECRET_ACCESS_KEY"],
        region=env["AWS_REGION"],
        language="en-US",
    )


def build_sarvam(env):
    """Sarvam — set SARVAM_API_KEY (sarvam.ai)."""
    return SarvamSTT(
        api_key=env["SARVAM_API_KEY"],
        language="en-IN",
    )


# --- registry: name -> (builder, required env vars) -------------------------
# An empty env list means the vendor is Agora-managed / key-less.
REGISTRY: Dict[str, Tuple[Callable, List[str]]] = {
    "deepgram":     (build_deepgram,     []),
    "ares":         (build_ares,         []),
    "assemblyai":   (build_assemblyai,   ["ASSEMBLYAI_API_KEY"]),
    "speechmatics": (build_speechmatics, ["SPEECHMATICS_API_KEY"]),
    "openai":       (build_openai,       ["OPENAI_STT_API_KEY"]),
    "microsoft":    (build_microsoft,    ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"]),
    "google":       (build_google,       ["GOOGLE_APPLICATION_CREDENTIALS_JSON", "GOOGLE_PROJECT_ID", "GOOGLE_LOCATION"]),
    "gemini":       (build_gemini,       ["GEMINI_STT_API_KEY"]),
    "amazon":       (build_amazon,       ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]),
    "sarvam":       (build_sarvam,       ["SARVAM_API_KEY"]),
}


def available() -> List[str]:
    return sorted(REGISTRY)


def required_env(name: str) -> List[str]:
    return list(REGISTRY[name][1])


def needs_key(name: str) -> bool:
    return bool(REGISTRY[name][1])


def build_vendor(
    name: str,
    env: Optional[Dict[str, str]] = None,
    keywords: Optional[List[str]] = None,
):
    """Build the selected vendor; raises ValueError naming any missing env vars."""
    env = env if env is not None else os.environ
    if name not in REGISTRY:
        raise ValueError(f"unknown {CATEGORY} vendor '{name}'; choose one of {available()}")
    builder, required = REGISTRY[name]
    missing = [var for var in required if not env.get(var)]
    if missing:
        raise ValueError(
            f"{CATEGORY} vendor '{name}' requires environment variable(s): {', '.join(missing)}"
        )
    if name == "ares":
        return builder(env, keywords=keywords)
    return builder(env)
