import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Adjust based on traffic. 100% in dev, 10% in prod.
  tracesSampleRate: process.env.NODE_ENV === "development" ? 1.0 : 0.1,

  // Privacy: do NOT capture IP addresses or request headers.
  // This app is private/single-user — we don't need PII to debug.
  sendDefaultPii: false,

  enableLogs: true,

  // Tag environment so Sentry dashboards can separate preview vs production.
  environment: process.env.NEXT_PUBLIC_VERCEL_ENV || process.env.NODE_ENV,
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
