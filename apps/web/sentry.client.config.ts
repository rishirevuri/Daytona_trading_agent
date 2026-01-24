/**
 * Sentry client-side configuration for Next.js.
 *
 * This file configures Sentry for browser-side error tracking
 * and performance monitoring.
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Performance monitoring
  tracesSampleRate: 1.0,

  // Session replay
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  // Only enable in production
  enabled: process.env.NODE_ENV === "production",

  // Filter out non-critical errors
  beforeSend(event) {
    // Don't send chunk load errors
    if (event.exception?.values?.[0]?.type === "ChunkLoadError") {
      return null;
    }
    return event;
  },

  integrations: [
    Sentry.replayIntegration({
      maskAllText: false,
      blockAllMedia: false,
    }),
  ],
});
