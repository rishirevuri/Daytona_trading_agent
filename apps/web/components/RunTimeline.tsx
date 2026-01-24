"use client";

import { useEffect, useRef, useState } from "react";
import {
  Check,
  Clock,
  Database,
  LineChart,
  FileText,
  AlertCircle,
} from "lucide-react";

interface TimelineStep {
  id: string;
  label: string;
  status: "pending" | "running" | "completed" | "error";
  duration?: number;
  message?: string;
}

interface RunTimelineProps {
  runId: string;
  onComplete?: () => void;
}

const STEPS: Omit<TimelineStep, "status">[] = [
  { id: "sandbox", label: "Creating Sandbox" },
  { id: "data", label: "Loading Data" },
  { id: "signals", label: "Generating Signals" },
  { id: "backtest", label: "Running Backtest" },
  { id: "metrics", label: "Calculating Metrics" },
  { id: "report", label: "Generating Report" },
];

export function RunTimeline({ runId, onComplete }: RunTimelineProps) {
  const [steps, setSteps] = useState<TimelineStep[]>(
    STEPS.map((s) => ({ ...s, status: "pending" }))
  );
  const [currentStep, setCurrentStep] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const logsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const eventSource = new EventSource(`/api/runs/${runId}/logs`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "log") {
        setLogs((prev) => [...prev, data.message]);

        // Update step based on log content
        updateStepFromLog(data.message);

        // Auto-scroll
        if (logsRef.current) {
          logsRef.current.scrollTop = logsRef.current.scrollHeight;
        }
      } else if (data.type === "complete") {
        // Mark all steps as complete or error based on status
        if (data.status === "completed") {
          setSteps((prev) =>
            prev.map((s) => ({ ...s, status: "completed" }))
          );
        } else {
          setSteps((prev) =>
            prev.map((s, i) =>
              i === currentStep
                ? { ...s, status: "error" }
                : i < currentStep
                ? { ...s, status: "completed" }
                : s
            )
          );
        }
        onComplete?.();
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => eventSource.close();
  }, [runId]);

  function updateStepFromLog(message: string) {
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes("creating sandbox") || lowerMessage.includes("[1/6]")) {
      moveToStep(0);
    } else if (lowerMessage.includes("loading data") || lowerMessage.includes("[2/6]")) {
      moveToStep(1);
    } else if (lowerMessage.includes("creating strategy") || lowerMessage.includes("[3/6]")) {
      moveToStep(2);
    } else if (lowerMessage.includes("running backtest") || lowerMessage.includes("[4/6]")) {
      moveToStep(3);
    } else if (lowerMessage.includes("calculating") || lowerMessage.includes("[5/6]")) {
      moveToStep(4);
    } else if (lowerMessage.includes("generating report") || lowerMessage.includes("[6/6]")) {
      moveToStep(5);
    }
  }

  function moveToStep(stepIndex: number) {
    setCurrentStep(stepIndex);
    setSteps((prev) =>
      prev.map((s, i) => ({
        ...s,
        status: i < stepIndex ? "completed" : i === stepIndex ? "running" : "pending",
      }))
    );
  }

  return (
    <div className="space-y-6">
      {/* Timeline */}
      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border" />

        <div className="space-y-4">
          {steps.map((step, index) => (
            <TimelineItem key={step.id} step={step} index={index} />
          ))}
        </div>
      </div>

      {/* Live Logs */}
      <div className="bg-card border border-border rounded-lg">
        <div className="px-4 py-2 border-b border-border text-sm font-medium">
          Live Output
        </div>
        <div
          ref={logsRef}
          className="h-48 overflow-y-auto p-4 font-mono text-xs text-muted-foreground log-viewer"
        >
          {logs.map((log, i) => (
            <div key={i} className="mb-1">
              {log}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TimelineItem({
  step,
  index,
}: {
  step: TimelineStep;
  index: number;
}) {
  const icons: Record<string, React.ReactNode> = {
    sandbox: <Database className="w-4 h-4" />,
    data: <Database className="w-4 h-4" />,
    signals: <LineChart className="w-4 h-4" />,
    backtest: <LineChart className="w-4 h-4" />,
    metrics: <LineChart className="w-4 h-4" />,
    report: <FileText className="w-4 h-4" />,
  };

  const statusStyles = {
    pending: "bg-muted text-muted-foreground border-border",
    running: "bg-blue-500/20 text-blue-400 border-blue-500 animate-pulse",
    completed: "bg-green-500/20 text-green-400 border-green-500",
    error: "bg-red-500/20 text-red-400 border-red-500",
  };

  const statusIcons = {
    pending: <Clock className="w-4 h-4" />,
    running: <Clock className="w-4 h-4 animate-spin" />,
    completed: <Check className="w-4 h-4" />,
    error: <AlertCircle className="w-4 h-4" />,
  };

  return (
    <div className="relative pl-10">
      <div
        className={`absolute left-2 w-5 h-5 rounded-full border-2 flex items-center justify-center ${
          statusStyles[step.status]
        }`}
      >
        {statusIcons[step.status]}
      </div>

      <div
        className={`p-3 rounded-lg border ${
          step.status === "running"
            ? "border-blue-500/30 bg-blue-500/5"
            : "border-border"
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">
              {icons[step.id]}
            </span>
            <span className="font-medium">{step.label}</span>
          </div>
          {step.duration && (
            <span className="text-xs text-muted-foreground">
              {(step.duration / 1000).toFixed(1)}s
            </span>
          )}
        </div>
        {step.message && (
          <div className="mt-1 text-sm text-muted-foreground">
            {step.message}
          </div>
        )}
      </div>
    </div>
  );
}
