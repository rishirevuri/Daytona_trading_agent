"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  RefreshCw,
  Download,
  ExternalLink,
  Volume2,
} from "lucide-react";
import { formatDate } from "@/lib/utils";

interface Run {
  id: string;
  status: string;
  config: Record<string, any>;
  metrics: Record<string, any> | null;
  sandboxId: string | null;
  snapshotId: string | null;
  sentryTraceId: string | null;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  strategy: {
    id: string;
    name: string;
    description: string;
  };
  artifacts: Artifact[];
  logs: Log[];
}

interface Artifact {
  id: string;
  type: string;
  filename: string;
  mimeType: string;
  size: number;
  createdAt: string;
}

interface Log {
  id: string;
  level: string;
  message: string;
  timestamp: string;
}

export default function RunDetailPage() {
  const params = useParams();
  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchRun();
  }, [params.id]);

  useEffect(() => {
    if (run?.status === "running" || run?.status === "pending") {
      startLogStreaming();
    }
  }, [run?.status]);

  async function fetchRun() {
    try {
      const res = await fetch(`/api/runs/${params.id}`);
      if (!res.ok) throw new Error("Run not found");
      const data = await res.json();
      setRun(data);
    } catch (error) {
      console.error("Error fetching run:", error);
    } finally {
      setLoading(false);
    }
  }

  function startLogStreaming() {
    if (isStreaming) return;
    setIsStreaming(true);

    const eventSource = new EventSource(`/api/runs/${params.id}/logs`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "log") {
        setRun((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            logs: [
              ...prev.logs,
              {
                id: data.id,
                level: data.level,
                message: data.message,
                timestamp: data.timestamp,
              },
            ],
          };
        });

        // Auto-scroll to bottom
        logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
      } else if (data.type === "complete") {
        setRun((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            status: data.status,
            metrics: data.metrics,
          };
        });
        eventSource.close();
        setIsStreaming(false);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setIsStreaming(false);
    };

    return () => {
      eventSource.close();
      setIsStreaming(false);
    };
  }

  async function handleReproduce() {
    try {
      const res = await fetch(`/api/runs/${params.id}/reproduce`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to reproduce");
      const data = await res.json();
      window.location.href = `/runs/${data.id}`;
    } catch (error) {
      console.error("Error reproducing run:", error);
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12 text-muted-foreground">Loading...</div>
    );
  }

  if (!run) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">Run not found</p>
        <Link href="/" className="text-primary hover:underline">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const isRunning = run.status === "running" || run.status === "pending";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href={`/strategies/${run.strategy.id}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to {run.strategy.name}
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">Run {run.id.slice(0, 8)}</h1>
            <p className="text-muted-foreground mt-1">
              {run.strategy.name} - {formatDate(run.createdAt)}
            </p>
          </div>
          <div className="flex gap-2">
            {run.status === "completed" && (
              <button
                onClick={handleReproduce}
                className="inline-flex items-center gap-2 px-3 py-2 border border-border rounded-md hover:bg-muted transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Reproduce
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Status Banner */}
      <StatusBanner status={run.status} isStreaming={isStreaming} />

      {/* Metrics */}
      {run.metrics && (
        <div className="bg-card border border-border rounded-lg p-4">
          <h2 className="font-semibold mb-4">Performance Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <MetricItem label="Sharpe" value={run.metrics.sharpe} format="number" />
            <MetricItem label="Sortino" value={run.metrics.sortino} format="number" />
            <MetricItem
              label="Total Return"
              value={run.metrics.total_return}
              format="percent"
            />
            <MetricItem
              label="Max Drawdown"
              value={run.metrics.max_drawdown}
              format="percent"
            />
            <MetricItem label="CAGR" value={run.metrics.cagr} format="percent" />
            <MetricItem
              label="Win Rate"
              value={run.metrics.win_rate}
              format="percent"
            />
          </div>
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Logs */}
        <div className="bg-card border border-border rounded-lg">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h2 className="font-semibold">Logs</h2>
            {isStreaming && (
              <span className="text-xs text-blue-400 flex items-center gap-1">
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                Streaming
              </span>
            )}
          </div>
          <div className="h-96 overflow-y-auto log-viewer p-4 font-mono text-sm">
            {run.logs.length === 0 ? (
              <div className="text-muted-foreground">No logs yet...</div>
            ) : (
              run.logs.map((log) => (
                <LogLine key={log.id} log={log} />
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </div>

        {/* Artifacts & Config */}
        <div className="space-y-6">
          {/* Artifacts */}
          <div className="bg-card border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="font-semibold">Artifacts</h2>
            </div>
            {run.artifacts.length === 0 ? (
              <div className="p-4 text-muted-foreground text-sm">
                No artifacts yet
              </div>
            ) : (
              <div className="divide-y divide-border">
                {run.artifacts.map((artifact) => (
                  <ArtifactRow key={artifact.id} artifact={artifact} runId={run.id} />
                ))}
              </div>
            )}
          </div>

          {/* Run Info */}
          <div className="bg-card border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="font-semibold">Run Info</h2>
            </div>
            <div className="p-4 space-y-2 text-sm">
              <InfoRow label="Status" value={run.status} />
              <InfoRow label="Started" value={run.startedAt ? formatDate(run.startedAt) : "Not started"} />
              <InfoRow label="Completed" value={run.completedAt ? formatDate(run.completedAt) : "Not completed"} />
              <InfoRow label="Sandbox ID" value={run.sandboxId || "N/A"} />
              {run.sentryTraceId && (
                <InfoRow
                  label="Sentry Trace"
                  value={
                    <a
                      href={`https://sentry.io/trace/${run.sentryTraceId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline flex items-center gap-1"
                    >
                      View Trace <ExternalLink className="w-3 h-3" />
                    </a>
                  }
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusBanner({
  status,
  isStreaming,
}: {
  status: string;
  isStreaming: boolean;
}) {
  const configs: Record<string, { bg: string; text: string; message: string }> = {
    pending: {
      bg: "bg-yellow-500/10 border-yellow-500/30",
      text: "text-yellow-400",
      message: "Waiting to start...",
    },
    running: {
      bg: "bg-blue-500/10 border-blue-500/30",
      text: "text-blue-400",
      message: "Backtest in progress...",
    },
    completed: {
      bg: "bg-green-500/10 border-green-500/30",
      text: "text-green-400",
      message: "Backtest completed successfully",
    },
    failed: {
      bg: "bg-red-500/10 border-red-500/30",
      text: "text-red-400",
      message: "Backtest failed",
    },
  };

  const config = configs[status] || configs.pending;

  return (
    <div className={`border rounded-lg p-4 ${config.bg}`}>
      <div className={`font-medium ${config.text}`}>{config.message}</div>
    </div>
  );
}

function MetricItem({
  label,
  value,
  format,
}: {
  label: string;
  value: number | undefined;
  format: "number" | "percent";
}) {
  let displayValue = "N/A";
  let isPositive = true;

  if (value !== undefined) {
    if (format === "percent") {
      displayValue = `${(value * 100).toFixed(1)}%`;
      isPositive = label === "Max Drawdown" ? value < 0.1 : value > 0;
    } else {
      displayValue = value.toFixed(2);
      isPositive = value > 0;
    }
  }

  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div
        className={`text-lg font-semibold ${
          value === undefined
            ? "text-muted-foreground"
            : isPositive
            ? "text-green-500"
            : "text-red-500"
        }`}
      >
        {displayValue}
      </div>
    </div>
  );
}

function LogLine({ log }: { log: Log }) {
  const levelColors: Record<string, string> = {
    info: "text-blue-400",
    warn: "text-yellow-400",
    error: "text-red-400",
    debug: "text-gray-400",
  };

  return (
    <div className="flex gap-2 mb-1">
      <span className="text-muted-foreground text-xs whitespace-nowrap">
        {new Date(log.timestamp).toLocaleTimeString()}
      </span>
      <span className={`${levelColors[log.level] || "text-foreground"}`}>
        {log.message}
      </span>
    </div>
  );
}

function ArtifactRow({ artifact, runId }: { artifact: Artifact; runId: string }) {
  return (
    <div className="flex items-center justify-between px-4 py-2">
      <div>
        <div className="font-medium text-sm">{artifact.filename}</div>
        <div className="text-xs text-muted-foreground">
          {artifact.mimeType} - {(artifact.size / 1024).toFixed(1)} KB
        </div>
      </div>
      <a
        href={`/api/runs/${runId}/artifacts?file=${artifact.filename}`}
        className="text-muted-foreground hover:text-foreground"
      >
        <Download className="w-4 h-4" />
      </a>
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
