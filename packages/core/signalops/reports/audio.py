"""
Audio briefing generation for backtest results.

Generates text summaries that can be converted to speech using ElevenLabs.
"""

from dataclasses import dataclass
from typing import Optional
import os
import requests


@dataclass
class AudioBriefing:
    """Audio briefing data."""

    script: str
    audio_bytes: Optional[bytes] = None
    duration_seconds: Optional[float] = None


class AudioBriefingGenerator:
    """Generate audio briefings for backtest results."""

    ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    DEFAULT_MODEL_ID = "eleven_multilingual_v2"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize generator.

        Args:
            api_key: ElevenLabs API key (defaults to ELEVENLABS_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

    def generate_script(
        self,
        strategy_name: str,
        metrics: dict,
        comparison: Optional[dict] = None,
        warnings: Optional[list[str]] = None,
    ) -> str:
        """Generate briefing script from metrics.

        Args:
            strategy_name: Name of the strategy
            metrics: Metrics dictionary with sharpe, total_return, etc.
            comparison: Optional comparison to previous run
            warnings: Optional list of warnings

        Returns:
            Briefing script text
        """
        script_parts = []

        # Opening
        script_parts.append(f"Here's your backtest briefing for {strategy_name}.")

        # Main metrics
        sharpe = metrics.get("sharpe", 0)
        total_return = metrics.get("total_return", 0) * 100
        max_drawdown = metrics.get("max_drawdown", 0) * 100
        win_rate = metrics.get("win_rate", 0) * 100

        script_parts.append(
            f"The strategy achieved a Sharpe ratio of {sharpe:.2f} "
            f"with a total return of {total_return:.1f} percent."
        )

        script_parts.append(
            f"Maximum drawdown was {max_drawdown:.1f} percent "
            f"and the win rate came in at {win_rate:.0f} percent."
        )

        # Comparison
        if comparison and "sharpe" in comparison:
            prev_sharpe = comparison.get("previous_sharpe", 0)
            sharpe_change = sharpe - prev_sharpe

            if sharpe_change > 0:
                script_parts.append(
                    f"Compared to the previous run, the Sharpe ratio improved by "
                    f"{abs(sharpe_change):.2f} points."
                )
            elif sharpe_change < 0:
                script_parts.append(
                    f"Compared to the previous run, the Sharpe ratio decreased by "
                    f"{abs(sharpe_change):.2f} points."
                )

        # Assessment
        if sharpe >= 2:
            script_parts.append(
                "This is an excellent result with strong risk-adjusted returns."
            )
        elif sharpe >= 1:
            script_parts.append(
                "This is a good result with acceptable risk-adjusted returns."
            )
        elif sharpe >= 0.5:
            script_parts.append(
                "This is a moderate result. Consider optimizing the strategy parameters."
            )
        else:
            script_parts.append(
                "The risk-adjusted returns are below optimal levels. "
                "Review the strategy design and parameters."
            )

        # Warnings
        if warnings:
            num_warnings = len(warnings)
            script_parts.append(
                f"Note: There {'is' if num_warnings == 1 else 'are'} "
                f"{num_warnings} warning{'s' if num_warnings > 1 else ''} to review."
            )

            # Include first warning if only one
            if num_warnings == 1:
                script_parts.append(warnings[0])

        # Closing
        script_parts.append("That's your briefing. Good luck with your research!")

        return " ".join(script_parts)

    def generate_audio(
        self,
        script: str,
        voice_id: Optional[str] = None,
    ) -> bytes:
        """Generate audio from script using ElevenLabs.

        Args:
            script: Text to convert to speech
            voice_id: Optional voice ID override

        Returns:
            Audio bytes (MP3 format)

        Raises:
            ValueError: If API key not configured
            RuntimeError: If API call fails
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")

        voice_id = voice_id or self.DEFAULT_VOICE_ID

        response = requests.post(
            f"{self.ELEVENLABS_API_URL}/text-to-speech/{voice_id}",
            headers={
                "Content-Type": "application/json",
                "xi-api-key": self.api_key,
            },
            json={
                "text": script,
                "model_id": self.DEFAULT_MODEL_ID,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "style": 0.3,
                    "use_speaker_boost": True,
                },
            },
            timeout=60,
        )

        if not response.ok:
            raise RuntimeError(f"ElevenLabs API error: {response.text}")

        return response.content

    def create_briefing(
        self,
        strategy_name: str,
        metrics: dict,
        comparison: Optional[dict] = None,
        warnings: Optional[list[str]] = None,
        generate_audio: bool = True,
    ) -> AudioBriefing:
        """Create complete audio briefing.

        Args:
            strategy_name: Name of the strategy
            metrics: Metrics dictionary
            comparison: Optional comparison data
            warnings: Optional warnings list
            generate_audio: Whether to generate audio (requires API key)

        Returns:
            AudioBriefing with script and optional audio
        """
        script = self.generate_script(
            strategy_name, metrics, comparison, warnings
        )

        audio_bytes = None
        if generate_audio and self.api_key:
            try:
                audio_bytes = self.generate_audio(script)
            except Exception as e:
                print(f"Warning: Audio generation failed: {e}")

        return AudioBriefing(
            script=script,
            audio_bytes=audio_bytes,
        )

    def estimate_duration(self, script: str) -> float:
        """Estimate audio duration in seconds.

        Args:
            script: Script text

        Returns:
            Estimated duration in seconds
        """
        # Average speaking rate is about 150 words per minute
        words = len(script.split())
        return (words / 150) * 60
