/**
 * ElevenLabs integration for audio briefings.
 *
 * Generates spoken summaries of backtest results.
 */

interface AudioBriefingParams {
  strategyName: string;
  metrics: {
    sharpe: number;
    total_return: number;
    max_drawdown: number;
    win_rate: number;
  };
  comparison?: {
    previous_sharpe: number;
    sharpe_change: number;
  };
  warnings?: string[];
}

interface ElevenLabsResponse {
  audio: Buffer;
  contentType: string;
}

const ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1";
const DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"; // Rachel voice
const DEFAULT_MODEL_ID = "eleven_multilingual_v2";

/**
 * Generate a text summary for TTS.
 */
export function generateBriefingScript(params: AudioBriefingParams): string {
  const { strategyName, metrics, comparison, warnings } = params;

  let script = `Here's your backtest briefing for ${strategyName}. `;

  // Main results
  const returnPercent = (metrics.total_return * 100).toFixed(1);
  const drawdownPercent = (metrics.max_drawdown * 100).toFixed(1);
  const winRatePercent = (metrics.win_rate * 100).toFixed(0);

  script += `The strategy achieved a Sharpe ratio of ${metrics.sharpe.toFixed(2)} `;
  script += `with a total return of ${returnPercent} percent. `;
  script += `Maximum drawdown was ${drawdownPercent} percent `;
  script += `and the win rate came in at ${winRatePercent} percent. `;

  // Comparison to previous run
  if (comparison) {
    const changeDirection =
      comparison.sharpe_change > 0 ? "improved" : "decreased";
    const changePercent = Math.abs(comparison.sharpe_change * 100).toFixed(0);
    script += `Compared to the previous run, the Sharpe ratio ${changeDirection} by ${changePercent} percent. `;
  }

  // Performance assessment
  if (metrics.sharpe >= 2) {
    script += `This is an excellent result with strong risk-adjusted returns. `;
  } else if (metrics.sharpe >= 1) {
    script += `This is a good result with acceptable risk-adjusted returns. `;
  } else if (metrics.sharpe >= 0.5) {
    script += `This is a moderate result. Consider optimizing the strategy. `;
  } else {
    script += `The risk-adjusted returns are below optimal levels. Review the strategy parameters. `;
  }

  // Warnings
  if (warnings && warnings.length > 0) {
    script += `Note: There are ${warnings.length} warning${warnings.length > 1 ? "s" : ""} to review. `;
    if (warnings.length <= 2) {
      script += warnings.join(". ") + ". ";
    }
  }

  // Closing
  script += `That's your briefing. Good luck with your research!`;

  return script;
}

/**
 * Generate audio using ElevenLabs API.
 */
export async function generateAudio(
  text: string,
  voiceId: string = DEFAULT_VOICE_ID
): Promise<ElevenLabsResponse> {
  const apiKey = process.env.ELEVENLABS_API_KEY;

  if (!apiKey) {
    throw new Error("ELEVENLABS_API_KEY environment variable is required");
  }

  const response = await fetch(
    `${ELEVENLABS_API_URL}/text-to-speech/${voiceId}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "xi-api-key": apiKey,
      },
      body: JSON.stringify({
        text,
        model_id: DEFAULT_MODEL_ID,
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.8,
          style: 0.3,
          use_speaker_boost: true,
        },
      }),
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`ElevenLabs API error: ${error}`);
  }

  const audioBuffer = await response.arrayBuffer();

  return {
    audio: Buffer.from(audioBuffer),
    contentType: "audio/mpeg",
  };
}

/**
 * Generate a complete audio briefing for a backtest run.
 */
export async function generateBriefing(
  params: AudioBriefingParams
): Promise<{ audio: Buffer; script: string; contentType: string }> {
  const script = generateBriefingScript(params);

  // Check script length (ElevenLabs has limits)
  if (script.length > 500) {
    console.warn(
      `Briefing script is ${script.length} chars, may exceed free tier limits`
    );
  }

  const { audio, contentType } = await generateAudio(script);

  return {
    audio,
    script,
    contentType,
  };
}

/**
 * Get available voices from ElevenLabs.
 */
export async function getVoices(): Promise<
  Array<{ voiceId: string; name: string }>
> {
  const apiKey = process.env.ELEVENLABS_API_KEY;

  if (!apiKey) {
    throw new Error("ELEVENLABS_API_KEY environment variable is required");
  }

  const response = await fetch(`${ELEVENLABS_API_URL}/voices`, {
    headers: {
      "xi-api-key": apiKey,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to fetch voices");
  }

  const data = await response.json();

  return data.voices.map((voice: any) => ({
    voiceId: voice.voice_id,
    name: voice.name,
  }));
}

/**
 * Check ElevenLabs API quota/usage.
 */
export async function checkQuota(): Promise<{
  characterCount: number;
  characterLimit: number;
  remainingCharacters: number;
}> {
  const apiKey = process.env.ELEVENLABS_API_KEY;

  if (!apiKey) {
    throw new Error("ELEVENLABS_API_KEY environment variable is required");
  }

  const response = await fetch(`${ELEVENLABS_API_URL}/user/subscription`, {
    headers: {
      "xi-api-key": apiKey,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to fetch subscription info");
  }

  const data = await response.json();

  return {
    characterCount: data.character_count,
    characterLimit: data.character_limit,
    remainingCharacters: data.character_limit - data.character_count,
  };
}
