/**
 * API routes for managing strategies.
 *
 * POST /api/strategies - Create a new strategy
 * GET /api/strategies - List all strategies
 */

import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const { name, description, code, config } = body;

    if (!name || !code) {
      return NextResponse.json(
        { error: "Name and code are required" },
        { status: 400 }
      );
    }

    const strategy = await prisma.strategy.create({
      data: {
        name,
        description: description || "",
        code,
        config: JSON.stringify(config || {}),
      },
    });

    return NextResponse.json(strategy, { status: 201 });
  } catch (error) {
    console.error("Error creating strategy:", error);
    return NextResponse.json(
      { error: "Failed to create strategy" },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get("limit") || "50");
    const offset = parseInt(searchParams.get("offset") || "0");

    const strategies = await prisma.strategy.findMany({
      take: limit,
      skip: offset,
      orderBy: { createdAt: "desc" },
      include: {
        runs: {
          take: 1,
          orderBy: { createdAt: "desc" },
          select: {
            id: true,
            status: true,
            metrics: true,
            createdAt: true,
          },
        },
        _count: {
          select: { runs: true },
        },
      },
    });

    // Parse metrics for each strategy's latest run
    const formattedStrategies = strategies.map((strategy) => {
      const latestRun = strategy.runs[0];
      let latestMetrics = null;

      if (latestRun?.metrics) {
        try {
          latestMetrics = JSON.parse(latestRun.metrics);
        } catch {
          // Ignore parse errors
        }
      }

      return {
        id: strategy.id,
        name: strategy.name,
        description: strategy.description,
        createdAt: strategy.createdAt,
        updatedAt: strategy.updatedAt,
        runCount: strategy._count.runs,
        latestRun: latestRun
          ? {
              id: latestRun.id,
              status: latestRun.status,
              createdAt: latestRun.createdAt,
              metrics: latestMetrics,
            }
          : null,
      };
    });

    const total = await prisma.strategy.count();

    return NextResponse.json({
      strategies: formattedStrategies,
      pagination: {
        total,
        limit,
        offset,
        hasMore: offset + strategies.length < total,
      },
    });
  } catch (error) {
    console.error("Error listing strategies:", error);
    return NextResponse.json(
      { error: "Failed to list strategies" },
      { status: 500 }
    );
  }
}
