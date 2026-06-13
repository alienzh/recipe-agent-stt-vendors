"""Vendor registry — data-driven switchboard over the A4.1 STT vendors."""
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from agora_agent.agentkit import vendors as V

CATEGORY = "STT"   # one of: STT | LLM | TTS | REALTIME  (per repo)


@dataclass
class VendorSpec:
    cls: Callable[..., Any]
    creds: Dict[str, str] = field(default_factory=dict)   # sdk_field -> ENV_VAR (required, no default)
    defaults: Dict[str, Any] = field(default_factory=dict)  # sdk_field -> default value
    model_field: Optional[str] = None   # field overridden by {CATEGORY}_MODEL
    voice_field: Optional[str] = None   # field overridden by {CATEGORY}_VOICE


SPECS: Dict[str, VendorSpec] = {
  "deepgram":    VendorSpec(V.DeepgramSTT, {}, {"model": "nova-3", "language": "en"}, model_field="model"),
  "ares":        VendorSpec(V.AresSTT, {}, {}),
  "assemblyai":  VendorSpec(V.AssemblyAISTT, {"api_key": "ASSEMBLYAI_API_KEY"}, {"language": "en"}),
  "speechmatics":VendorSpec(V.SpeechmaticsSTT, {"api_key": "SPEECHMATICS_API_KEY"}, {"language": "en"}),
  "openai":      VendorSpec(V.OpenAISTT, {"api_key": "OPENAI_STT_API_KEY"},
                   {"model": "gpt-4o-transcribe", "prompt": "Transcribe the audio.", "language": "en"},
                   model_field="model"),
  "microsoft":   VendorSpec(V.MicrosoftSTT, {"key": "AZURE_SPEECH_KEY", "region": "AZURE_SPEECH_REGION"}, {"language": "en-US"}),
  "google":      VendorSpec(V.GoogleSTT, {"adc_credentials_string": "GOOGLE_APPLICATION_CREDENTIALS_JSON", "project_id": "GOOGLE_PROJECT_ID", "location": "GOOGLE_LOCATION"}, {"language": "en-US"}),
  "amazon":      VendorSpec(V.AmazonSTT, {"access_key": "AWS_ACCESS_KEY_ID", "secret_key": "AWS_SECRET_ACCESS_KEY", "region": "AWS_REGION"}, {"language": "en-US"}),
  "sarvam":      VendorSpec(V.SarvamSTT, {"api_key": "SARVAM_API_KEY"}, {"language": "en-IN"}),
}


def available() -> List[str]:
    return sorted(SPECS)


def required_env(name: str) -> List[str]:
    return list(SPECS[name].creds.values())


def build_vendor(name: str, env: Optional[Dict[str, str]] = None):
    env = env if env is not None else os.environ
    if name not in SPECS:
        raise ValueError(f"unknown {CATEGORY} vendor '{name}'; choose one of {available()}")
    spec = SPECS[name]
    kwargs: Dict[str, Any] = dict(spec.defaults)
    # generic model/voice overrides
    if spec.model_field and env.get(f"{CATEGORY}_MODEL"):
        kwargs[spec.model_field] = env[f"{CATEGORY}_MODEL"]
    if spec.voice_field and env.get(f"{CATEGORY}_VOICE"):
        kwargs[spec.voice_field] = env[f"{CATEGORY}_VOICE"]
    # required creds + infra from env
    missing: List[str] = []
    for sdk_field, var in spec.creds.items():
        val = env.get(var)
        if not val:
            missing.append(var)
        else:
            kwargs[sdk_field] = val
    if missing:
        raise ValueError(
            f"{CATEGORY} vendor '{name}' requires environment variable(s): {', '.join(missing)}"
        )
    return spec.cls(**kwargs)
