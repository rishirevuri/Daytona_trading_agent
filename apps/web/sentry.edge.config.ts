/**
 * Sentry Edge runtime configuration for Next.js.
 *
 * This file configures Sentry for Edge runtime (middleware, etc.)
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,

  // Performance monitoring
  tracesSampleRate: 1.0,

  // Only enable in production
  enabled: process.env.NODE_ENV === "production",
});
