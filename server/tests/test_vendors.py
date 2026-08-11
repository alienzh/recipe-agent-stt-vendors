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


def test_ares_emits_keywords():
    vendor = R.build_vendor(
        "ares",
        {"STT_KEYWORDS": '["Agora", "Conversational AI", "RTC"]'},
    )

    assert vendor.to_config() == {
        "vendor": "ares",
        "params": {"keywords": ["Agora", "Conversational AI", "RTC"]},
    }


def test_ares_omits_empty_keywords():
    assert R.build_vendor("ares", {}).to_config() == {"vendor": "ares"}
    assert R.build_vendor("ares", {"STT_KEYWORDS": "[]"}).to_config() == {
        "vendor": "ares"
    }


@pytest.mark.parametrize(
    "value",
    [
        "not-json",
        '{"keyword": "Agora"}',
        '["Agora", 7]',
        '["Agora", ""]',
    ],
)
def test_managed_hotword_vendors_reject_invalid_keywords(value):
    with pytest.raises(
        ValueError,
        match="STT_KEYWORDS must be a JSON array of non-empty strings",
    ):
        R.build_vendor("ares", {"STT_KEYWORDS": value})
