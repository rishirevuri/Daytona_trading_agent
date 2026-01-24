/**
 * Sentry server-side configuration for Next.js.
 *
 * This file configures Sentry for server-side error tracking
 * and API route performance monitoring.
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,

  // Performance monitoring
  tracesSampleRate: 1.0,

  // Only enable in production
  enabled: process.env.NODE_ENV === "production",

  // Attach additional context
  beforeSend(event, hint) {
    // Add custom context for backtest errors
    if (hint.originalException instanceof Error) {
      const error = hint.originalException;
      if (error.message.includes("backtest")) {
        Sentry.setContext("backtest", {
          errorType: "backtest_failure",
        });
      }
    }
    return event;
  },

  // Configure profiling
  profilesSampleRate: 0.1,
});
