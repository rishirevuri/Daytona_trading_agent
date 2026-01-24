"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Play,
  Clock,
  TrendingUp,
  TrendingDown,
  ExternalLink,
  GitBranch,
} from "lucide-react";
import { formatDate, getStatusColor } from "@/lib/utils";

interface Strategy {
  id: string;
  name: string;
  description: string;
  code: string;
  config: Record<string, any>;
  createdAt: string;
  runs: Run[];
}

interface Run {
  id: string;
  status: string;
  metrics: {
    sharpe?: number;
    sortino?: number;
    total_return?: number;
    max_drawdown?: number;
    cagr?: number;
    win_rate?: number;
  } | null;
  createdAt: string;
  completedAt: string | null;
  commitSha: string | null;
  prUrl: string | null;
}

export default function StrategyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningNewRun, setRunningNewRun] = useState(false);

  useEffect(() => {
    fetchStrategy();
  }, [params.id]);

  async function fetchStrategy() {
    try {
      const res = await fetch(`/api/strategies/${params.id}`);
      if (!res.ok) throw new Error("Strategy not found");
      const data = await res.json();
      setStrategy(data);
    } catch (error) {
      console.error("Error fetching strategy:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleRunExperiment() {
    if (!strategy) return;
    setRunningNewRun(true);

    try {
      const res = await fetch(`/api/strategies/${strategy.id}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          config: strategy.config,
        }),
      });

      if (!res.ok) throw new Error("Failed to start run");
      const data = await res.json();
      router.push(`/runs/${data.id}`);
    } catch (error) {
      console.error("Error starting run:", error);
      setRunningNewRun(false);
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12 text-muted-foreground">Loading...</div>
    );
  }

  if (!strategy) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">Strategy not found</p>
        <Link href="/" className="text-primary hover:underline">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const latestRun = strategy.runs[0];
  const metrics = latestRun?.metrics;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">{strategy.name}</h1>
            <p className="text-muted-foreground mt-1">
              {strategy.description || "No description"}
            </p>
          </div>
          <button
            onClick={handleRunExperiment}
            disabled={runningNewRun}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            {runningNewRun ? "Starting..." : "Run Experiment"}
          </button>
        </div>
      </div>

      {/* Metrics Overview */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <MetricCard
            label="Sharpe Ratio"
            value={metrics.sharpe?.toFixed(2) || "N/A"}
            positive={Boolean(metrics.sharpe && metrics.sharpe > 0)}
          />
          <MetricCard
            label="Sortino Ratio"
            value={metrics.sortino?.toFixed(2) || "N/A"}
            positive={Boolean(metrics.sortino && metrics.sortino > 0)}
          />
          <MetricCard
            label="Total Return"
            value={
              metrics.total_return
                ? `${(metrics.total_return * 100).toFixed(1)}%`
                : "N/A"
            }
            positive={Boolean(metrics.total_return && metrics.total_return > 0)}
          />
          <MetricCard
            label="Max Drawdown"
            value={
              metrics.max_drawdown
                ? `${(metrics.max_drawdown * 100).toFixed(1)}%`
                : "N/A"
            }
            positive={metrics.max_drawdown ? metrics.max_drawdown < 0.1 : true}
          />
          <MetricCard
            label="CAGR"
            value={
              metrics.cagr ? `${(metrics.cagr * 100).toFixed(1)}%` : "N/A"
            }
            positive={Boolean(metrics.cagr && metrics.cagr > 0)}
          />
          <MetricCard
            label="Win Rate"
            value={
              metrics.win_rate
                ? `${(metrics.win_rate * 100).toFixed(0)}%`
                : "N/A"
            }
            positive={Boolean(metrics.win_rate && metrics.win_rate > 0.5)}
          />
        </div>
      )}

      {/* Run History */}
      <div className="bg-card border border-border rounded-lg">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="font-semibold">Run History</h2>
        </div>

        {strategy.runs.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            No runs yet. Click &ldquo;Run Experiment&rdquo; to start your first backtest.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {strategy.runs.map((run) => (
              <RunRow key={run.id} run={run} />
            ))}
          </div>
        )}
      </div>

      {/* Strategy Code Preview */}
      <div className="bg-card border border-border rounded-lg">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="font-semibold">Strategy Code</h2>
        </div>
        <pre className="p-4 overflow-x-auto text-sm font-mono text-muted-foreground max-h-96">
          {strategy.code}
        </pre>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive: boolean;
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div
        className={`text-xl font-bold ${
          value === "N/A"
            ? "text-muted-foreground"
            : positive
            ? "text-green-500"
            : "text-red-500"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

function RunRow({ run }: { run: Run }) {
  const statusColors: Record<string, string> = {
    completed: "bg-green-500",
    running: "bg-blue-500 animate-pulse",
    failed: "bg-red-500",
    pending: "bg-yellow-500",
  };

  return (
    <Link
      href={`/runs/${run.id}`}
      className="flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors"
    >
      <div className="flex items-center gap-4">
        <div
          className={`w-2 h-2 rounded-full ${
            statusColors[run.status] || statusColors.pending
          }`}
        />
        <div>
          <div className="font-medium">Run {run.id.slice(0, 8)}</div>
          <div className="text-sm text-muted-foreground">
            {formatDate(run.createdAt)}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        {run.metrics && (
          <>
            <div className="text-right">
              <div className="text-sm font-medium">
                {run.metrics.sharpe?.toFixed(2) || "N/A"}
              </div>
              <div className="text-xs text-muted-foreground">Sharpe</div>
            </div>
            <div className="text-right">
              <div
                className={`text-sm font-medium ${
                  run.metrics.total_return && run.metrics.total_return > 0
                    ? "text-green-500"
                    : "text-red-500"
                }`}
              >
                {run.metrics.total_return
                  ? `${(run.metrics.total_return * 100).toFixed(1)}%`
                  : "N/A"}
              </div>
              <div className="text-xs text-muted-foreground">Return</div>
            </div>
          </>
        )}

        {run.prUrl && (
          <a
            href={run.prUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground"
            onClick={(e) => e.stopPropagation()}
          >
            <GitBranch className="w-4 h-4" />
          </a>
        )}

        <span className="text-xs text-muted-foreground capitalize">
          {run.status}
        </span>
      </div>
    </Link>
  );
}
