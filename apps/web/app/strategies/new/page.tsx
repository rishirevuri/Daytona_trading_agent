"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Save, Play } from "lucide-react";

const DEFAULT_STRATEGY_CODE = `"""
Moving Average Crossover Strategy
Buy when fast MA crosses above slow MA, sell when it crosses below.
"""

import pandas as pd
import numpy as np

def generate_signals(prices: pd.DataFrame, config: dict) -> pd.Series:
    """
    Generate trading signals based on moving average crossover.

    Args:
        prices: DataFrame with 'close' column
        config: Strategy configuration with 'fast_window' and 'slow_window'

    Returns:
        Series of signals: 1 (long), 0 (flat), -1 (short)
    """
    fast_window = config.get('fast_window', 10)
    slow_window = config.get('slow_window', 30)

    close = prices['close']

    # Calculate moving averages
    fast_ma = close.rolling(window=fast_window).mean()
    slow_ma = close.rolling(window=slow_window).mean()

    # Generate signals
    signals = pd.Series(0, index=prices.index)
    signals[fast_ma > slow_ma] = 1   # Long when fast > slow
    signals[fast_ma < slow_ma] = -1  # Short when fast < slow

    return signals
`;

const DEFAULT_CONFIG = {
  fast_window: 10,
  slow_window: 30,
  ticker: "SPY",
  start_date: "2020-01-01",
  end_date: "2023-12-31",
  initial_capital: 100000,
  commission: 0.001,
};

export default function NewStrategyPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [code, setCode] = useState(DEFAULT_STRATEGY_CODE);
  const [config, setConfig] = useState(JSON.stringify(DEFAULT_CONFIG, null, 2));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave(runAfterSave = false) {
    if (!name.trim()) {
      setError("Strategy name is required");
      return;
    }

    try {
      JSON.parse(config);
    } catch {
      setError("Invalid JSON configuration");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const res = await fetch("/api/strategies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          code,
          config: JSON.parse(config),
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to create strategy");
      }

      const strategy = await res.json();

      if (runAfterSave) {
        // Start a run immediately
        const runRes = await fetch(`/api/strategies/${strategy.id}/runs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ config: JSON.parse(config) }),
        });

        if (runRes.ok) {
          const run = await runRes.json();
          router.push(`/runs/${run.id}`);
          return;
        }
      }

      router.push(`/strategies/${strategy.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <h1 className="text-2xl font-bold">Create New Strategy</h1>
        <p className="text-muted-foreground mt-1">
          Define your trading strategy code and configuration
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      {/* Form */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Basic Info & Code */}
        <div className="space-y-6">
          {/* Name & Description */}
          <div className="bg-card border border-border rounded-lg p-4 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Strategy Name <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., MA Crossover SPY"
                className="w-full px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this strategy does..."
                rows={2}
                className="w-full px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
            </div>
          </div>

          {/* Strategy Code */}
          <div className="bg-card border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="font-semibold">Strategy Code (Python)</h2>
            </div>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-96 p-4 bg-background font-mono text-sm focus:outline-none resize-none"
              spellCheck={false}
            />
          </div>
        </div>

        {/* Right Column - Configuration */}
        <div className="space-y-6">
          {/* Configuration */}
          <div className="bg-card border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="font-semibold">Configuration (JSON)</h2>
            </div>
            <textarea
              value={config}
              onChange={(e) => setConfig(e.target.value)}
              className="w-full h-64 p-4 bg-background font-mono text-sm focus:outline-none resize-none"
              spellCheck={false}
            />
          </div>

          {/* Config Help */}
          <div className="bg-muted/50 rounded-lg p-4">
            <h3 className="font-medium mb-2">Configuration Options</h3>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li><code className="text-primary">fast_window</code> - Fast MA period</li>
              <li><code className="text-primary">slow_window</code> - Slow MA period</li>
              <li><code className="text-primary">ticker</code> - Stock symbol to backtest</li>
              <li><code className="text-primary">start_date</code> - Backtest start date</li>
              <li><code className="text-primary">end_date</code> - Backtest end date</li>
              <li><code className="text-primary">initial_capital</code> - Starting capital</li>
              <li><code className="text-primary">commission</code> - Commission rate (0.001 = 0.1%)</li>
            </ul>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={() => handleSave(false)}
              disabled={saving}
              className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 transition-colors disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {saving ? "Saving..." : "Save Strategy"}
            </button>
            <button
              onClick={() => handleSave(true)}
              disabled={saving}
              className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              {saving ? "Saving..." : "Save & Run"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
