import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Propagate Vercel env to client-side Sentry config.
  env: {
    NEXT_PUBLIC_VERCEL_ENV: process.env.VERCEL_ENV,
  },
};

export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT || "ai-life-web",
  authToken: process.env.SENTRY_AUTH_TOKEN,

  // Upload a wider set of source maps for readable stack traces.
  widenClientFileUpload: true,

  // Only log upload output in CI — keeps local builds quiet.
  silent: !process.env.CI,

  // Route Sentry requests through Next.js server to bypass ad blockers.
  tunnelRoute: "/monitoring",

  // Hide source maps from the public bundle.
  sourcemaps: {
    disable: false,
    deleteSourcemapsAfterUpload: true,
  },

  // Disable telemetry from the Sentry build plugin itself.
  telemetry: false,

  disableLogger: true,
});
