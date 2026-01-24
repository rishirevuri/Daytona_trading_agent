import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: Date | string): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

export function formatNumber(value: number, decimals: number = 2): string {
  return value.toFixed(decimals);
}

export function formatPercent(value: number, decimals: number = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function getStatusColor(status: string): string {
  switch (status) {
    case "completed":
      return "text-green-500";
    case "running":
      return "text-blue-500";
    case "failed":
      return "text-red-500";
    case "pending":
    default:
      return "text-muted-foreground";
  }
}

export function getMetricColor(metric: string, value: number): string {
  if (metric === "sharpe" || metric === "sortino") {
    if (value >= 2) return "text-green-500";
    if (value >= 1) return "text-yellow-500";
    return "text-red-500";
  }
  if (metric === "maxDrawdown") {
    if (value <= 0.1) return "text-green-500";
    if (value <= 0.2) return "text-yellow-500";
    return "text-red-500";
  }
  if (metric === "pbo") {
    if (value <= 0.3) return "text-green-500";
    if (value <= 0.5) return "text-yellow-500";
    return "text-red-500";
  }
  return "text-foreground";
}
