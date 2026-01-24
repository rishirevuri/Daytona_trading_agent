"use client";

import {
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart2,
  Target,
  AlertTriangle,
} from "lucide-react";

interface Metrics {
  sharpe: number;
  sortino: number;
  total_return: number;
  max_drawdown: number;
  cagr: number;
  win_rate: number;
  profit_factor?: number;
  volatility?: number;
  calmar?: number;
  avg_win?: number;
  avg_loss?: number;
}

interface MetricsDisplayProps {
  metrics: Metrics;
  comparison?: Metrics; // For comparing train vs test
  showComparison?: boolean;
}

export function MetricsDisplay({
  metrics,
  comparison,
  showComparison = false,
}: MetricsDisplayProps) {
  const primaryMetrics = [
    {
      key: "sharpe",
      label: "Sharpe Ratio",
      icon: TrendingUp,
      format: (v: number) => v.toFixed(2),
      threshold: { good: 1, great: 2 },
      higher: true,
    },
    {
      key: "sortino",
      label: "Sortino Ratio",
      icon: TrendingUp,
      format: (v: number) => v.toFixed(2),
      threshold: { good: 1.5, great: 3 },
      higher: true,
    },
    {
      key: "total_return",
      label: "Total Return",
      icon: BarChart2,
      format: (v: number) => `${(v * 100).toFixed(1)}%`,
      threshold: { good: 0.1, great: 0.3 },
      higher: true,
    },
    {
      key: "max_drawdown",
      label: "Max Drawdown",
      icon: TrendingDown,
      format: (v: number) => `${(v * 100).toFixed(1)}%`,
      threshold: { good: 0.15, great: 0.1 },
      higher: false,
    },
    {
      key: "cagr",
      label: "CAGR",
      icon: Activity,
      format: (v: number) => `${(v * 100).toFixed(1)}%`,
      threshold: { good: 0.1, great: 0.2 },
      higher: true,
    },
    {
      key: "win_rate",
      label: "Win Rate",
      icon: Target,
      format: (v: number) => `${(v * 100).toFixed(0)}%`,
      threshold: { good: 0.5, great: 0.55 },
      higher: true,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {primaryMetrics.map((metric) => {
          const value = metrics[metric.key as keyof Metrics];
          const compValue = comparison?.[metric.key as keyof Metrics];

          return (
            <MetricCard
              key={metric.key}
              label={metric.label}
              value={value}
              comparisonValue={showComparison ? compValue : undefined}
              format={metric.format}
              icon={metric.icon}
              threshold={metric.threshold}
              higherIsBetter={metric.higher}
            />
          );
        })}
      </div>

      {/* Secondary Metrics */}
      {(metrics.profit_factor || metrics.volatility || metrics.calmar) && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {metrics.profit_factor && (
            <SecondaryMetric
              label="Profit Factor"
              value={metrics.profit_factor.toFixed(2)}
            />
          )}
          {metrics.volatility && (
            <SecondaryMetric
              label="Volatility"
              value={`${(metrics.volatility * 100).toFixed(1)}%`}
            />
          )}
          {metrics.calmar && (
            <SecondaryMetric
              label="Calmar Ratio"
              value={metrics.calmar.toFixed(2)}
            />
          )}
          {metrics.avg_win && metrics.avg_loss && (
            <SecondaryMetric
              label="Win/Loss Ratio"
              value={(Math.abs(metrics.avg_win / metrics.avg_loss)).toFixed(2)}
            />
          )}
        </div>
      )}

      {/* Comparison Table (Train vs Test) */}
      {showComparison && comparison && (
        <ComparisonTable metrics={metrics} comparison={comparison} />
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  comparisonValue,
  format,
  icon: Icon,
  threshold,
  higherIsBetter,
}: {
  label: string;
  value: number | undefined;
  comparisonValue?: number;
  format: (v: number) => string;
  icon: React.ElementType;
  threshold: { good: number; great: number };
  higherIsBetter: boolean;
}) {
  if (value === undefined) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 text-muted-foreground mb-2">
          <Icon className="w-4 h-4" />
          <span className="text-xs">{label}</span>
        </div>
        <div className="text-xl font-bold text-muted-foreground">N/A</div>
      </div>
    );
  }

  const isGood = higherIsBetter
    ? value >= threshold.good
    : value <= threshold.good;
  const isGreat = higherIsBetter
    ? value >= threshold.great
    : value <= threshold.great;

  const colorClass = isGreat
    ? "text-green-500"
    : isGood
    ? "text-yellow-500"
    : "text-red-500";

  // Calculate change from comparison
  let changeIndicator = null;
  if (comparisonValue !== undefined) {
    const change = ((value - comparisonValue) / Math.abs(comparisonValue)) * 100;
    const isPositiveChange = higherIsBetter ? change > 0 : change < 0;
    changeIndicator = (
      <span
        className={`text-xs ${
          isPositiveChange ? "text-green-400" : "text-red-400"
        }`}
      >
        {change > 0 ? "+" : ""}
        {change.toFixed(0)}%
      </span>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Icon className="w-4 h-4" />
          <span className="text-xs">{label}</span>
        </div>
        {changeIndicator}
      </div>
      <div className={`text-xl font-bold ${colorClass}`}>{format(value)}</div>
    </div>
  );
}

function SecondaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-muted/50 rounded-lg p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  );
}

function ComparisonTable({
  metrics,
  comparison,
}: {
  metrics: Metrics;
  comparison: Metrics;
}) {
  const rows = [
    { key: "sharpe", label: "Sharpe Ratio", format: (v: number) => v.toFixed(2) },
    { key: "sortino", label: "Sortino Ratio", format: (v: number) => v.toFixed(2) },
    {
      key: "total_return",
      label: "Total Return",
      format: (v: number) => `${(v * 100).toFixed(1)}%`,
    },
    {
      key: "max_drawdown",
      label: "Max Drawdown",
      format: (v: number) => `${(v * 100).toFixed(1)}%`,
    },
    {
      key: "win_rate",
      label: "Win Rate",
      format: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
  ];

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-border">
        <h3 className="font-semibold">In-Sample vs Out-of-Sample</h3>
      </div>
      <table className="w-full">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th className="px-4 py-2">Metric</th>
            <th className="px-4 py-2">In-Sample</th>
            <th className="px-4 py-2">Out-of-Sample</th>
            <th className="px-4 py-2">Degradation</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const isValue = metrics[row.key as keyof Metrics] as number;
            const oosValue = comparison[row.key as keyof Metrics] as number;
            const degradation =
              isValue && oosValue
                ? ((isValue - oosValue) / Math.abs(isValue)) * 100
                : 0;
            const isOverfit = degradation > 20;

            return (
              <tr key={row.key} className="border-t border-border">
                <td className="px-4 py-2 text-sm">{row.label}</td>
                <td className="px-4 py-2 font-medium">
                  {isValue !== undefined ? row.format(isValue) : "N/A"}
                </td>
                <td className="px-4 py-2 font-medium">
                  {oosValue !== undefined ? row.format(oosValue) : "N/A"}
                </td>
                <td className="px-4 py-2">
                  {degradation !== 0 && (
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                        isOverfit
                          ? "bg-red-500/20 text-red-400"
                          : degradation > 10
                          ? "bg-yellow-500/20 text-yellow-400"
                          : "bg-green-500/20 text-green-400"
                      }`}
                    >
                      {isOverfit && <AlertTriangle className="w-3 h-3" />}
                      {degradation > 0 ? "-" : "+"}
                      {Math.abs(degradation).toFixed(0)}%
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
