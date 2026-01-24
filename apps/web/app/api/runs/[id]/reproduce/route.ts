/**
 * API route for reproducing a run from its snapshot.
 *
 * POST /api/runs/[id]/reproduce - Re-run experiment with same config
 */

import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const { id: originalRunId } = await params;

    // Get original run
    const originalRun = await prisma.run.findUnique({
      where: { id: originalRunId },
      include: {
        strategy: true,
      },
    });

    if (!originalRun) {
      return NextResponse.json(
        { error: "Original run not found" },
        { status: 404 }
      );
    }

    if (originalRun.status !== "completed") {
      return NextResponse.json(
        { error: "Can only reproduce completed runs" },
        { status: 400 }
      );
    }

    // Create new run with same config
    const newRun = await prisma.run.create({
      data: {
        strategyId: originalRun.strategyId,
        status: "pending",
        config: originalRun.config,
        // Link to original for reproducibility tracking
        snapshotId: originalRun.snapshotId,
        imageDigest: originalRun.imageDigest,
      },
    });

    // Store reproduction metadata in logs
    await prisma.log.create({
      data: {
        runId: newRun.id,
        level: "info",
        message: `Reproducing run ${originalRunId}`,
        metadata: JSON.stringify({
          originalRunId,
          originalSandboxId: originalRun.sandboxId,
          originalSnapshotId: originalRun.snapshotId,
        }),
      },
    });

    // In production, this would trigger the actual backtest
    // using the same snapshot/configuration

    return NextResponse.json(
      {
        id: newRun.id,
        status: newRun.status,
        originalRunId,
        message: "Reproduction started",
      },
      { status: 201 }
    );
  } catch (error) {
    console.error("Error reproducing run:", error);
    return NextResponse.json(
      { error: "Failed to reproduce run" },
      { status: 500 }
    );
  }
}
