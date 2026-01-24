/**
 * API routes for a specific strategy.
 *
 * GET /api/strategies/[id] - Get strategy details
 * PUT /api/strategies/[id] - Update strategy
 * DELETE /api/strategies/[id] - Delete strategy
 */

import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;

    const strategy = await prisma.strategy.findUnique({
      where: { id },
      include: {
        runs: {
          orderBy: { createdAt: "desc" },
          take: 20,
          select: {
            id: true,
            status: true,
            metrics: true,
            createdAt: true,
            completedAt: true,
            commitSha: true,
            prUrl: true,
          },
        },
      },
    });

    if (!strategy) {
      return NextResponse.json(
        { error: "Strategy not found" },
        { status: 404 }
      );
    }

    // Parse config and run metrics
    const formattedStrategy = {
      ...strategy,
      config: JSON.parse(strategy.config || "{}"),
      runs: strategy.runs.map((run) => ({
        ...run,
        metrics: run.metrics ? JSON.parse(run.metrics) : null,
      })),
    };

    return NextResponse.json(formattedStrategy);
  } catch (error) {
    console.error("Error fetching strategy:", error);
    return NextResponse.json(
      { error: "Failed to fetch strategy" },
      { status: 500 }
    );
  }
}

export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;
    const body = await request.json();

    const { name, description, code, config } = body;

    const strategy = await prisma.strategy.update({
      where: { id },
      data: {
        ...(name && { name }),
        ...(description !== undefined && { description }),
        ...(code && { code }),
        ...(config && { config: JSON.stringify(config) }),
      },
    });

    return NextResponse.json(strategy);
  } catch (error) {
    console.error("Error updating strategy:", error);
    return NextResponse.json(
      { error: "Failed to update strategy" },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;

    await prisma.strategy.delete({
      where: { id },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting strategy:", error);
    return NextResponse.json(
      { error: "Failed to delete strategy" },
      { status: 500 }
    );
  }
}
