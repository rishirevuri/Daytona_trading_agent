"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, TrendingUp, TrendingDown, Clock, Play } from "lucide-react";
import { formatDate, getStatusColor, getMetricColor } from "@/lib/utils";

interface Strategy {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  runCount: number;
  latestRun: {
    id: string;
    status: string;
    createdAt: string;
    metrics: {
      sharpe?: number;
      total_return?: number;
      max_drawdown?: number;
    } | null;
  } | null;
}

export default function Dashboard() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStrategies();
  }, []);

  async function fetchStrategies() {
    try {
      const res = await fetch("/api/strategies");
      const data = await res.json();
      setStrategies(data.strategies || []);
    } catch (error) {
      console.error("Error fetching strategies:", error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Strategies</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage and run your trading strategy experiments
          </p>
        </div>
        <Link
          href="/strategies/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Strategy
        </Link>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Strategies"
          value={strategies.length}
          icon={<TrendingUp className="w-5 h-5" />}
        />
        <StatCard
          label="Total Runs"
          value={strategies.reduce((acc, s) => acc + s.runCount, 0)}
          icon={<Play className="w-5 h-5" />}
        />
        <StatCard
          label="Avg Sharpe"
          value={calculateAvgSharpe(strategies)}
          icon={<TrendingUp className="w-5 h-5" />}
        />
        <StatCard
          label="Active Runs"
          value={strategies.filter((s) => s.latestRun?.status === "running").length}
          icon={<Clock className="w-5 h-5" />}
        />
      </div>

      {/* Strategy List */}
      {loading ? (
        <div className="text-center py-12 text-muted-foreground">
          Loading strategies...
        </div>
      ) : strategies.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {strategies.map((strategy) => (
            <StrategyCard key={strategy.id} strategy={strategy} />
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-3">
        <div className="text-muted-foreground">{icon}</div>
        <div>
          <div className="text-2xl font-bold">{value}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      </div>
    </div>
  );
}

function StrategyCard({ strategy }: { strategy: Strategy }) {
  const latestRun = strategy.latestRun;
  const metrics = latestRun?.metrics;

  return (
    <Link
      href={`/strategies/${strategy.id}`}
      className="block bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold">{strategy.name}</h3>
          <p className="text-sm text-muted-foreground line-clamp-1">
            {strategy.description || "No description"}
          </p>
        </div>
        {latestRun && (
          <StatusBadge status={latestRun.status} />
        )}
      </div>

      {metrics ? (
        <div className="grid grid-cols-3 gap-2 mb-3">
          <MetricDisplay
            label="Sharpe"
            value={metrics.sharpe?.toFixed(2) || "N/A"}
            color={getMetricColor("sharpe", metrics.sharpe || 0)}
          />
          <MetricDisplay
            label="Return"
            value={
              metrics.total_return
                ? `${(metrics.total_return * 100).toFixed(1)}%`
                : "N/A"
            }
            color={
              metrics.total_return && metrics.total_return > 0
                ? "text-green-500"
                : "text-red-500"
            }
          />
          <MetricDisplay
            label="Max DD"
            value={
              metrics.max_drawdown
                ? `${(metrics.max_drawdown * 100).toFixed(1)}%`
                : "N/A"
            }
            color={getMetricColor("maxDrawdown", metrics.max_drawdown || 0)}
          />
        </div>
      ) : (
        <div className="text-sm text-muted-foreground mb-3">No runs yet</div>
      )}

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{strategy.runCount} runs</span>
        <span>{formatDate(strategy.createdAt)}</span>
      </div>
    </Link>
  );
}

function MetricDisplay({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="text-center">
      <div className={`text-sm font-medium ${color}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: "bg-green-500/20 text-green-400",
    running: "bg-blue-500/20 text-blue-400",
    failed: "bg-red-500/20 text-red-400",
    pending: "bg-yellow-500/20 text-yellow-400",
  };

  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-medium ${
        colors[status] || colors.pending
      }`}
    >
      {status}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-16 bg-card border border-border rounded-lg">
      <TrendingUp className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
      <h3 className="text-lg font-semibold mb-2">No strategies yet</h3>
      <p className="text-muted-foreground mb-6">
        Create your first trading strategy to get started
      </p>
      <Link
        href="/strategies/new"
        className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
      >
        <Plus className="w-4 h-4" />
        Create Strategy
      </Link>
    </div>
  );
}

function calculateAvgSharpe(strategies: Strategy[]): string {
  const sharpes = strategies
    .map((s) => s.latestRun?.metrics?.sharpe)
    .filter((s): s is number => typeof s === "number");

  if (sharpes.length === 0) return "N/A";
  return (sharpes.reduce((a, b) => a + b, 0) / sharpes.length).toFixed(2);
}
