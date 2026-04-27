# Design Decisions — AI-Life UI

## Core decision (26 April 2026)

**Foundation: shadcn/ui `dashboard-01` block.**
**Aesthetic: Linear / Vercel / Resend / Stripe — neutral, dense, dark-first, one accent.**

This is a hard reset from the earlier glassmorphism direction. That direction produced inconsistent, decorative cards (rainbow gradients per domain, emoji headers, hand-rolled CSS). It didn't look award-winning — it looked like a hobby project.

The new direction:
- One canonical app shell (sidebar + sticky header), installed once from `pnpm dlx shadcn@latest add dashboard-01`.
- One set of primitives (`SectionCards`, `ChartAreaInteractive`, `DataTable`, `Sidebar`) reused across every domain.
- One accent colour (Violet `#8b5cf6` mapped to shadcn `--primary`).
- One radius scale (shadcn default, `--radius: 0.625rem`).
- shadcn tokens as the only source of truth — no parallel `--bg-0..3` / `--fg-0..3` / `--accent-*` variables.

## Why dashboard-01 over alternatives

Top 5 evaluated, April 2026:

| Template | Why considered | Verdict |
|---|---|---|
| shadcn `dashboard-01` | Official shadcn block, free, MIT, exact stack match | ✅ Winner |
| Tremor Raw | Best chart/KPI primitives | ⭐ Use Tremor patterns inside dashboard-01 if shadcn charts insufficient |
| TailAdmin Pro | 80k users, polished | ❌ Enterprise-admin aesthetic, not command centre |
| Horizon UI Shadcn | Polished AI starter | ❌ Commercial, opinionated, harder to customise |
| Vercel Admin Template | Official Vercel | ⭐ Reference only — dashboard-01 is more complete |

Decisive reasons for dashboard-01:
- One-command install: `pnpm dlx shadcn@latest add dashboard-01`
- Copy-paste — we own the code
- MIT, free forever
- Stack match: Next.js App Router + Tailwind v4 + Radix + Recharts + Lucide
- Maintained by the team that builds shadcn — won't go stale
- Defines the look most "award-winning" 2025-2026 dashboards copy

## Forbidden patterns (the reset)

These were in the previous version of this skill — they are now banned:

- ❌ `bg-gradient-to-br from-*-500/10 to-*-500/10` — rainbow gradients per domain
- ❌ `backdrop-blur-xl` glassmorphism cards
- ❌ `rounded-3xl` (24px)
- ❌ Domain-specific gradient palettes (Transit blue→purple, Travel purple→pink, etc.) — replace with single neutral `bg-card`
- ❌ Emoji prefixes in headings (`🚀 Card Title`)
- ❌ Per-domain bespoke layouts
- ❌ Parallel `--bg-0`, `--fg-0`, `--accent-*` CSS variables
- ❌ Big coloured status panels — use small `Badge` instead

## Standing decisions

1. **Animation** — minimal, state changes only. shadcn defaults handle dialogs/popovers. No hover scale, no decorative motion.
2. **Form validation** — on blur + on submit. shadcn `<Form>` + `react-hook-form` + `zod`.
3. **Empty states** — icon + one line of text. No "Get started!" CTAs, no custom illustrations. `<Skeleton />` while loading.
4. **Mobile** — same info as desktop, reflowed. Sidebar collapses to `<Sheet>`. No hamburger hiding critical functions.
5. **Component ownership**
   - `apps/web/components/ui/` — shadcn primitives (copied via CLI)
   - `apps/web/components/` — composed app-specific components (`app-sidebar.tsx`, `section-cards.tsx`)
   - `apps/web/app/dashboard/<domain>/` — one page per domain, all reuse the shell
   - `packages/ui/` — only if a primitive is genuinely used by another app
6. **Accessibility** — WCAG AA floor. shadcn primitives meet this; verify icon buttons have `aria-label`, inputs have `<Label>`.
7. **Dark mode only** — locked. No light theme.
8. **Charts** — shadcn `Chart` (Recharts). Single accent colour, muted gridlines.
9. **Icons** — Lucide only. `size={16}` inline, `size={18}` in buttons. Never emoji as iconography.
10. **Status colour** — small dot + short text (`text-amber-500`). Never large coloured panels.

## Pending decisions

- **Notifications:** `sonner` (shadcn-recommended toast) vs. inbox → lean toast for now.
- **Advanced charts:** Adopt Tremor Raw if shadcn charts insufficient.
- **User-selectable accent:** defer until requested.
- **Offline / PWA:** out of scope for now.

## Defer to specialist agents

- **Smart home device control UI** — Smart Home Specialist briefs requirements; this skill builds the surface
- **Property Finder listing layout** — Property Finder agent decides cards vs. table; this skill builds it inside dashboard-01
- **Finance dashboards** — Personal Finances agent specifies metrics; this skill renders them as `SectionCards` + `ChartAreaInteractive`
- **Photo grid** — Photos Librarian agent specifies layout; this skill implements it

---

**Last updated:** 26 April 2026 — pivoted from bespoke glassmorphism to shadcn dashboard-01 foundation.
