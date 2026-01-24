"use client";

import { useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  AlertCircle,
  FileText,
  BarChart2,
  Search,
} from "lucide-react";

interface AnalysisResult {
  ticker: string;
  sentiment: {
    score: number;
    positive_count: number;
    negative_count: number;
    confidence: number;
    key_phrases: string[];
  };
  price_reaction: {
    overnight_gap: number;
    day_1_return: number;
    day_5_return: number;
  };
  guidance_summary: string;
  risk_factors: string[];
}

export default function EarningsLensPage() {
  const [ticker, setTicker] = useState("");
  const [transcript, setTranscript] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  async function handleAnalyze() {
    if (!ticker || !transcript) return;
    setLoading(true);

    try {
      // In production, this would call an API endpoint
      // For demo, we'll simulate the analysis
      const mockResult: AnalysisResult = {
        ticker: ticker.toUpperCase(),
        sentiment: {
          score: Math.random() * 2 - 1, // -1 to 1
          positive_count: Math.floor(Math.random() * 50) + 10,
          negative_count: Math.floor(Math.random() * 30) + 5,
          confidence: Math.random() * 0.5 + 0.5,
          key_phrases: [
            "Strong momentum in our core business",
            "Exceeded expectations for the quarter",
            "Facing headwinds from currency exchange",
          ],
        },
        price_reaction: {
          overnight_gap: (Math.random() * 0.1 - 0.05),
          day_1_return: (Math.random() * 0.15 - 0.075),
          day_5_return: (Math.random() * 0.2 - 0.1),
        },
        guidance_summary:
          "We expect full-year revenue growth of 15-18% and are raising our EPS guidance to $4.50-$4.75.",
        risk_factors: [
          "Supply chain constraints may impact Q4 deliveries",
          "Foreign exchange headwinds expected to continue",
        ],
      };

      setResult(mockResult);
    } catch (error) {
      console.error("Analysis error:", error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">EarningsCall Lens</h1>
        <p className="text-muted-foreground mt-1">
          Analyze earnings call transcripts for sentiment and market correlation
        </p>
      </div>

      {/* Input Section */}
      <div className="bg-card border border-border rounded-lg p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Ticker</label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="AAPL"
              className="w-full px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="md:col-span-3">
            <label className="block text-sm font-medium mb-2">
              Paste Transcript
            </label>
            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Paste earnings call transcript here..."
              rows={4}
              className="w-full px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            />
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={loading || !ticker || !transcript}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          <Search className="w-4 h-4" />
          {loading ? "Analyzing..." : "Analyze Transcript"}
        </button>
      </div>

      {/* Results Section */}
      {result && (
        <div className="space-y-6">
          {/* Sentiment Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <SentimentCard sentiment={result.sentiment} />
            <PriceReactionCard priceReaction={result.price_reaction} />
            <ConfidenceCard confidence={result.sentiment.confidence} />
          </div>

          {/* Key Phrases */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Key Phrases
            </h3>
            <div className="space-y-2">
              {result.sentiment.key_phrases.map((phrase, i) => (
                <div
                  key={i}
                  className="p-3 bg-muted/50 rounded-md text-sm"
                >
                  &ldquo;{phrase}&rdquo;
                </div>
              ))}
            </div>
          </div>

          {/* Guidance & Risks */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-card border border-border rounded-lg p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <BarChart2 className="w-4 h-4" />
                Guidance Summary
              </h3>
              <p className="text-sm text-muted-foreground">
                {result.guidance_summary}
              </p>
            </div>

            <div className="bg-card border border-border rounded-lg p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-yellow-500" />
                Risk Factors
              </h3>
              {result.risk_factors.length > 0 ? (
                <ul className="space-y-2">
                  {result.risk_factors.map((risk, i) => (
                    <li
                      key={i}
                      className="text-sm text-muted-foreground flex items-start gap-2"
                    >
                      <span className="text-yellow-500">•</span>
                      {risk}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No significant risk factors identified
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Instructions */}
      {!result && (
        <div className="bg-muted/50 rounded-lg p-8 text-center">
          <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">
            How to Use EarningsCall Lens
          </h3>
          <p className="text-muted-foreground max-w-md mx-auto">
            Enter a ticker symbol and paste an earnings call transcript. The
            analyzer will extract sentiment, key guidance, and risk factors,
            then correlate with price movements.
          </p>
        </div>
      )}
    </div>
  );
}

function SentimentCard({
  sentiment,
}: {
  sentiment: AnalysisResult["sentiment"];
}) {
  const isPositive = sentiment.score > 0;
  const scorePercent = Math.abs(sentiment.score * 100).toFixed(0);

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Sentiment</h3>
        {isPositive ? (
          <TrendingUp className="w-5 h-5 text-green-500" />
        ) : (
          <TrendingDown className="w-5 h-5 text-red-500" />
        )}
      </div>

      <div
        className={`text-3xl font-bold mb-2 ${
          isPositive ? "text-green-500" : "text-red-500"
        }`}
      >
        {isPositive ? "+" : "-"}
        {scorePercent}%
      </div>

      <div className="text-sm text-muted-foreground space-y-1">
        <div className="flex justify-between">
          <span>Positive words:</span>
          <span className="text-green-400">{sentiment.positive_count}</span>
        </div>
        <div className="flex justify-between">
          <span>Negative words:</span>
          <span className="text-red-400">{sentiment.negative_count}</span>
        </div>
      </div>
    </div>
  );
}

function PriceReactionCard({
  priceReaction,
}: {
  priceReaction: AnalysisResult["price_reaction"];
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="font-semibold mb-4">Price Reaction</h3>

      <div className="space-y-3">
        <PriceMetric
          label="Overnight Gap"
          value={priceReaction.overnight_gap}
        />
        <PriceMetric
          label="Day 1 Return"
          value={priceReaction.day_1_return}
        />
        <PriceMetric
          label="Day 5 Return"
          value={priceReaction.day_5_return}
        />
      </div>
    </div>
  );
}

function PriceMetric({ label, value }: { label: string; value: number }) {
  const isPositive = value > 0;
  const displayValue = `${isPositive ? "+" : ""}${(value * 100).toFixed(2)}%`;

  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span
        className={`font-medium ${
          isPositive ? "text-green-500" : "text-red-500"
        }`}
      >
        {displayValue}
      </span>
    </div>
  );
}

function ConfidenceCard({ confidence }: { confidence: number }) {
  const confidencePercent = (confidence * 100).toFixed(0);
  const level =
    confidence >= 0.8
      ? "High"
      : confidence >= 0.6
      ? "Medium"
      : "Low";
  const color =
    confidence >= 0.8
      ? "text-green-500"
      : confidence >= 0.6
      ? "text-yellow-500"
      : "text-red-500";

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="font-semibold mb-4">Analysis Confidence</h3>

      <div className={`text-3xl font-bold mb-2 ${color}`}>
        {confidencePercent}%
      </div>

      <div className="text-sm text-muted-foreground">
        <span className={color}>{level}</span> confidence based on
        sentiment word density
      </div>

      {/* Confidence bar */}
      <div className="mt-4 h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full ${
            confidence >= 0.8
              ? "bg-green-500"
              : confidence >= 0.6
              ? "bg-yellow-500"
              : "bg-red-500"
          }`}
          style={{ width: `${confidence * 100}%` }}
        />
      </div>
    </div>
  );
}
