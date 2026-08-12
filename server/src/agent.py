"""
Agent — STT Vendors Recipe

High-level API for managing an Agora Conversational AI Agent whose STT leg is a
data-driven switchboard over every A4.1 STT vendor. The LLM and TTS legs stay on
the proven keyless configs; only the STT is swapped via `STT_VENDOR`.

Pipeline:  <STT_VENDOR> (default Deepgram, keyless) → OpenAI(gpt-4o-mini, keyless) → MiniMaxTTS

The default vendor (`deepgram`) is Agora-managed and keyless. Any BYO vendor
requires its credentials, which are validated in `start()` (not `__init__`, via
`build_vendor` raising `ValueError`) so `/get_config` stays key-less.
"""
import logging
import os
from typing import Any, Dict, Optional

from agora_agent import Area, AsyncAgora
from agora_agent.agentkit import Agent as AgoraAgent
from agora_agent.agentkit.vendors import OpenAI, MiniMaxTTS

from vendors import build_vendor

logger = logging.getLogger("uvicorn.error")


class Agent:
    """
    High-level wrapper for Agora Conversational AI Agent with a swappable STT leg.

    The STT vendor is selected via `STT_VENDOR` (default `deepgram`, keyless) and
    built from the data-driven registry in `vendors.py`. The LLM and TTS legs
    stay on the proven keyless configs.
    """

    def __init__(self):
        self.app_id = os.getenv("AGORA_APP_ID")
        self.app_certificate = os.getenv("AGORA_APP_CERTIFICATE")
        self.greeting = os.getenv(
            "AGENT_GREETING",
            "Hi! Talk to me and watch the event timeline light up.",
        )

        # The selected STT vendor (default `deepgram`, Agora-managed/keyless).
        # No credential validation here — that happens in start() via
        # build_vendor, so /get_config stays key-less.
        self.vendor = os.getenv("STT_VENDOR", "deepgram")

        if not self.app_id or not self.app_certificate:
            raise ValueError("AGORA_APP_ID and AGORA_APP_CERTIFICATE are required")

        self.client = AsyncAgora(
            area=Area.US,
            app_id=self.app_id,
            app_certificate=self.app_certificate,
        )

        # Track active sessions by agent_id
        self._sessions: Dict[str, Any] = {}

    async def start(
        self,
        channel_name: str,
        agent_uid: int,
        user_uid: int,
        vendor: Optional[str] = None,
        keywords: Optional[list[str]] = None,
        output_audio_codec: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start the agent with the selected STT vendor."""
        if not channel_name or not str(channel_name).strip():
            raise ValueError("channel_name is required and cannot be empty")
        if agent_uid <= 0:
            raise ValueError("agent_uid is required and cannot be empty")
        if user_uid <= 0:
            raise ValueError("user_uid is required and cannot be empty")

        # The in-UI switcher passes `vendor`; otherwise fall back to STT_VENDOR.
        selected = (vendor or self.vendor).strip()

        # Build the selected STT vendor from the registry. For a BYO vendor
        # without its credentials this raises ValueError listing the missing
        # environment variables — validated here in start(), not __init__.
        if keywords is not None:
            if selected != "ares":
                raise ValueError("keywords are only supported for the ares STT vendor")
            if not keywords or any(not isinstance(keyword, str) or not keyword.strip() for keyword in keywords):
                raise ValueError("keywords must be a non-empty list of non-empty strings")
            keywords = [keyword.strip() for keyword in keywords]

        stt = build_vendor(selected, keywords=keywords)
        stt_params = stt.to_config().get("params") or {}
        keywords = stt_params.get("keywords") or []
        greeting = self.greeting
        if keywords:
            sample = ", ".join(keywords[:3])
            greeting = (
                "Hi! To test keyword recognition, say a sentence containing "
                f"{sample}, then check the transcript."
            )

        llm = OpenAI(model="gpt-4o-mini")
        tts = MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")

        parameters = {
            "audio_scenario": "chorus",  # web client — ultra-low-latency chorus profile
            "data_channel": "rtm",
            "enable_error_message": True,
            "enable_metrics": True,
        }
        if isinstance(output_audio_codec, str) and output_audio_codec.strip():
            parameters["output_audio_codec"] = output_audio_codec.strip()

        agora_agent = AgoraAgent(
            client=self.client,
            greeting=greeting,
            failure_message="Please wait a moment.",
            max_history=50,
            turn_detection={
                "config": {
                    "speech_threshold": 0.5,
                    "start_of_speech": {
                        "mode": "vad",
                        "vad_config": {
                            "interrupt_duration_ms": 160,
                            "prefix_padding_ms": 300,
                        },
                    },
                    "end_of_speech": {
                        "mode": "vad",
                        "vad_config": {
                            "silence_duration_ms": 480,
                        },
                    },
                },
            },
            advanced_features={"enable_rtm": True},
            parameters=parameters,
        )

        agora_agent = (
            agora_agent
            .with_stt(stt)
            .with_llm(llm)
            .with_tts(tts)
        )

        session = agora_agent.create_async_session(
            channel=channel_name,
            agent_uid=str(agent_uid),
            remote_uids=[str(user_uid)],
            enable_string_uid=False,
            idle_timeout=30,
            expires_in=3600,
        )

        logger.info(
            "Starting agent channel=%s agent_uid=%s user_uid=%s",
            channel_name,
            agent_uid,
            user_uid,
        )

        try:
            agent_id = await session.start()
        except Exception:
            logger.exception(
                "Failed to start agent channel=%s agent_uid=%s user_uid=%s",
                channel_name,
                agent_uid,
                user_uid,
            )
            raise

        # Save session for later stop
        self._sessions[agent_id] = session

        logger.info(
            "Started agent agent_id=%s channel=%s",
            agent_id,
            channel_name,
        )

        return {
            "agent_id": agent_id,
            "channel_name": channel_name,
            "vendor": selected,
            "status": "started",
        }

    async def stop(self, agent_id: str) -> None:
        """Stop a running agent. Falls back to the stateless client path."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")

        session = self._sessions.pop(agent_id, None)
        if session:
            try:
                await session.stop()
                logger.info("Stopped agent from active session agent_id=%s", agent_id)
                return
            except Exception:
                logger.warning(
                    "Failed to stop agent from active session; falling back agent_id=%s",
                    agent_id,
                    exc_info=True,
                )

        logger.info("Stopping agent through client.stop_agent agent_id=%s", agent_id)
        await self.client.stop_agent(agent_id)
