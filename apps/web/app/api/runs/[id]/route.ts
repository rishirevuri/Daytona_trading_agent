/**
 * API routes for run details.
 *
 * GET /api/runs/[id] - Get run details
 * POST /api/runs/[id]/reproduce - Reproduce a run from snapshot
 */

import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;

    const run = await prisma.run.findUnique({
      where: { id },
      include: {
        strategy: {
          select: {
            id: true,
            name: true,
            description: true,
          },
        },
        artifacts: {
          select: {
            id: true,
            type: true,
            filename: true,
            mimeType: true,
            size: true,
            createdAt: true,
          },
        },
        logs: {
          orderBy: { timestamp: "asc" },
          take: 1000,
          select: {
            id: true,
            level: true,
            message: true,
            timestamp: true,
          },
        },
      },
    });

    if (!run) {
      return NextResponse.json({ error: "Run not found" }, { status: 404 });
    }

    // Parse JSON fields
    const formattedRun = {
      ...run,
      config: run.config ? JSON.parse(run.config) : null,
      metrics: run.metrics ? JSON.parse(run.metrics) : null,
    };

    return NextResponse.json(formattedRun);
  } catch (error) {
    console.error("Error fetching run:", error);
    return NextResponse.json(
      { error: "Failed to fetch run" },
      { status: 500 }
    );
  }
}
