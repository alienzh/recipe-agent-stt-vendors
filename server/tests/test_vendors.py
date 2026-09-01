import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import vendors as R  # noqa: E402

# vendors whose to_config() emits a "vendor" key, and the expected value.
# `openai` STT is exempt from the vendor-key check — the test only asserts its
# to_config() is a non-empty dict.
EXPECTED_VENDOR = {
    "deepgram": "deepgram",
    "ares": "ares",
    "assemblyai": "assemblyai",
    "speechmatics": "speechmatics",
    "microsoft": "microsoft",
    "google": "google",
    "gemini": "gemini",
    "amazon": "amazon",
    "sarvam": "sarvam",
}


def _dummy_env(name):
    return {var: "dummy" for var in R.required_env(name)}


def test_every_vendor_constructs_and_emits_config():
    for name in R.available():
        vendor = R.build_vendor(name, _dummy_env(name))
        cfg = vendor.to_config()
        assert isinstance(cfg, dict) and cfg, f"{name}: empty config"
        if name in EXPECTED_VENDOR:
            assert cfg.get("vendor") == EXPECTED_VENDOR[name], f"{name}: vendor mismatch"


def test_byo_vendor_missing_creds_raises():
    byo = [n for n in R.available() if R.required_env(n)]
    assert byo, "expected at least one BYO vendor"
    name = byo[0]
    try:
        R.build_vendor(name, {})
    except ValueError as e:
        assert R.required_env(name)[0] in str(e)
    else:
        raise AssertionError(f"{name} should raise when creds are absent")


def test_ares_emits_request_keywords():
    vendor = R.build_vendor(
        "ares",
        {},
        keywords=["Agora", "Conversational AI", "RTC"],
    )

    assert vendor.to_config() == {
        "vendor": "ares",
        "keywords": ["Agora", "Conversational AI", "RTC"],
    }


def test_ares_omits_keywords_by_default():
    assert R.build_vendor("ares", {}).to_config() == {"vendor": "ares"}


def test_gemini_uses_preview_defaults_and_routes_to_preview():
    config = R.build_vendor(
        "gemini",
        {"GEMINI_STT_API_KEY": "gemini-key"},
    ).to_config()

    assert config == {
        "vendor": "gemini",
        "params": {
            "api_key": "gemini-key",
            "model": "gemini-3.5-transcribe-live",
            "sample_rate": 16000,
        },
    }

    from agora_agent.agentkit.preview import required_preview_features

    assert required_preview_features({"asr": config}) == ["gemini-live"]


def test_gemini_accepts_common_model_override():
    config = R.build_vendor(
        "gemini",
        {
            "GEMINI_STT_API_KEY": "gemini-key",
            "STT_MODEL": "gemini-custom-model",
        },
    ).to_config()

    assert config["params"]["model"] == "gemini-custom-model"
