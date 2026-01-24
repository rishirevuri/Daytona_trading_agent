/**
 * API route for streaming run logs via Server-Sent Events (SSE).
 *
 * GET /api/runs/[id]/logs - Stream logs in real-time
 */

import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  const { id: runId } = await params;

  // Check if run exists
  const run = await prisma.run.findUnique({
    where: { id: runId },
    select: { id: true, status: true },
  });

  if (!run) {
    return NextResponse.json({ error: "Run not found" }, { status: 404 });
  }

  // Create SSE stream
  const encoder = new TextEncoder();
  let lastLogId: string | null = null;
  let isRunning = true;

  const stream = new ReadableStream({
    async start(controller) {
      // Send initial connection message
      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify({ type: "connected", runId })}\n\n`)
      );

      // Poll for new logs
      const pollInterval = setInterval(async () => {
        try {
          // Get new logs since last check
          const logs = await prisma.log.findMany({
            where: {
              runId,
              ...(lastLogId && {
                id: { gt: lastLogId },
              }),
            },
            orderBy: { timestamp: "asc" },
            take: 100,
          });

          // Send each log
          for (const log of logs) {
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: "log",
                  id: log.id,
                  level: log.level,
                  message: log.message,
                  timestamp: log.timestamp.toISOString(),
                })}\n\n`
              )
            );
            lastLogId = log.id;
          }

          // Check run status
          const currentRun = await prisma.run.findUnique({
            where: { id: runId },
            select: { status: true, metrics: true },
          });

          if (
            currentRun &&
            (currentRun.status === "completed" || currentRun.status === "failed")
          ) {
            // Send completion event
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: "complete",
                  status: currentRun.status,
                  metrics: currentRun.metrics
                    ? JSON.parse(currentRun.metrics)
                    : null,
                })}\n\n`
              )
            );

            isRunning = false;
            clearInterval(pollInterval);
            controller.close();
          }
        } catch (error) {
          console.error("SSE poll error:", error);
        }
      }, 1000); // Poll every second

      // Cleanup on close
      request.signal.addEventListener("abort", () => {
        isRunning = false;
        clearInterval(pollInterval);
        controller.close();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
