/**
 * API route for triggering strategy runs.
 *
 * POST /api/strategies/[id]/runs - Trigger a new experiment run
 */

import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { runBacktestInSandbox } from "@/lib/daytona";
import { generateExperimentConfig } from "@/lib/daytona-config";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const { id: strategyId } = await params;
    const body = await request.json();

    // Get strategy
    const strategy = await prisma.strategy.findUnique({
      where: { id: strategyId },
    });

    if (!strategy) {
      return NextResponse.json(
        { error: "Strategy not found" },
        { status: 404 }
      );
    }

    // Parse strategy config
    const strategyConfig = JSON.parse(strategy.config || "{}");

    // Override with request body config
    const runConfig = {
      ...strategyConfig,
      ...body.config,
    };

    // Create run record
    const run = await prisma.run.create({
      data: {
        strategyId,
        status: "pending",
        config: JSON.stringify(runConfig),
      },
    });

    // Start the backtest asynchronously
    // In production, this would be handled by a job queue
    runBacktestAsync(run.id, strategy, runConfig);

    return NextResponse.json(
      {
        id: run.id,
        status: run.status,
        message: "Run started",
      },
      { status: 201 }
    );
  } catch (error) {
    console.error("Error creating run:", error);
    return NextResponse.json(
      { error: "Failed to create run" },
      { status: 500 }
    );
  }
}

/**
 * Run backtest asynchronously (background job simulation).
 */
async function runBacktestAsync(
  runId: string,
  strategy: { id: string; name: string; code: string },
  config: Record<string, any>
) {
  try {
    // Update status to running
    await prisma.run.update({
      where: { id: runId },
      data: {
        status: "running",
        startedAt: new Date(),
      },
    });

    // Store logs
    const addLog = async (message: string, level: string = "info") => {
      await prisma.log.create({
        data: {
          runId,
          level,
          message,
        },
      });
    };

    await addLog("Starting backtest run...");

    // Generate experiment config
    const experimentConfig = generateExperimentConfig({
      strategyId: strategy.id,
      runId,
      strategyName: strategy.name,
      strategyParams: config.strategy || {},
      dataConfig: config.data || { source: "yahoo", symbol: "SPY", period: "5y" },
      backtestConfig: config.backtest,
    });

    // Run in Daytona sandbox
    const result = await runBacktestInSandbox({
      strategyCode: strategy.code,
      config: JSON.parse(experimentConfig),
      runId,
      strategyId: strategy.id,
      onLog: async (log) => {
        await addLog(log);
      },
    });

    if (result.success) {
      // Update run with results
      await prisma.run.update({
        where: { id: runId },
        data: {
          status: "completed",
          completedAt: new Date(),
          sandboxId: result.sandboxId,
          metrics: JSON.stringify(result.metrics || {}),
        },
      });

      // Store artifacts
      if (result.artifacts) {
        for (const [filename, content] of Object.entries(result.artifacts)) {
          const mimeType = filename.endsWith(".json")
            ? "application/json"
            : filename.endsWith(".csv")
            ? "text/csv"
            : filename.endsWith(".html")
            ? "text/html"
            : "application/octet-stream";

          await prisma.artifact.create({
            data: {
              runId,
              type: filename.replace(/\.[^.]+$/, ""),
              filename,
              path: `artifacts/${runId}/${filename}`,
              mimeType,
              size: content.length,
            },
          });
        }
      }

      await addLog("Backtest completed successfully", "info");
    } else {
      // Update run as failed
      await prisma.run.update({
        where: { id: runId },
        data: {
          status: "failed",
          completedAt: new Date(),
        },
      });

      await addLog(`Backtest failed: ${result.error}`, "error");
    }
  } catch (error) {
    console.error("Backtest error:", error);

    await prisma.run.update({
      where: { id: runId },
      data: {
        status: "failed",
        completedAt: new Date(),
      },
    });

    await prisma.log.create({
      data: {
        runId,
        level: "error",
        message: `Unexpected error: ${error instanceof Error ? error.message : "Unknown"}`,
      },
    });
  }
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { id: strategyId } = await params;
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get("limit") || "20");
    const offset = parseInt(searchParams.get("offset") || "0");

    const runs = await prisma.run.findMany({
      where: { strategyId },
      take: limit,
      skip: offset,
      orderBy: { createdAt: "desc" },
      select: {
        id: true,
        status: true,
        metrics: true,
        createdAt: true,
        startedAt: true,
        completedAt: true,
        commitSha: true,
        prUrl: true,
      },
    });

    const formattedRuns = runs.map((run) => ({
      ...run,
      metrics: run.metrics ? JSON.parse(run.metrics) : null,
    }));

    return NextResponse.json({ runs: formattedRuns });
  } catch (error) {
    console.error("Error listing runs:", error);
    return NextResponse.json(
      { error: "Failed to list runs" },
      { status: 500 }
    );
  }
}
