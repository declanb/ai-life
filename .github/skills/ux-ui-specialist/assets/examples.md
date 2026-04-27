# Examples — How to invoke the UX/UI Specialist

## How the skill activates

The skill is **auto-invoked** by the agent when your message contains UX/UI trigger words (ui, ux, dashboard, card, sidebar, table, chart, form, design, layout, shadcn, accessibility). You can also invoke explicitly by asking for it.

---

## 1. Bootstrap the foundation (do this first)

> "Set up the shadcn dashboard-01 foundation in apps/web and migrate the existing globals.css to use shadcn tokens only. Delete my legacy `--bg-0..3` / `--fg-0..3` / `--accent-*` variables and keep Geist + violet `--primary`."

The agent will:
1. Run `pnpm dlx shadcn@latest init` (Neutral / New York / CSS vars / App Router)
2. Run `pnpm dlx shadcn@latest add dashboard-01`
3. Edit `apps/web/app/globals.css` — drop legacy tokens, set `--primary` to violet
4. Move existing `app/page.tsx` content under `app/dashboard/page.tsx`
5. Verify the dev server still builds

---

## 2. Add a domain page inside the shell

> "Add a Property Finder page at `/dashboard/property` using the dashboard-01 layout. Include a 4-card KPI strip (active searches, new matches today, viewings this week, shortlist count) and a data table of current shortlist."

The agent will:
1. Create `apps/web/app/dashboard/property/page.tsx`
2. Reuse `<SectionCards>` from dashboard-01, swapping in property KPI props
3. Reuse `<DataTable>` with property-specific columns (address, rent, BER, commute, status, action)
4. Add a sidebar nav item in `components/app-sidebar.tsx`
5. Wire to `/api/v1/property-finder/...` endpoints (or stub data if backend not ready)

---

## 3. Migrate an existing dashboard

> "Refactor `TransitDashboard.tsx` to live under `/dashboard/transit` using the new shell. Drop the gradient cards and emoji headers — make it look like Vercel's logs page. Keep the live commute logic and 30s auto-refresh."

The agent will:
1. Move logic into `app/dashboard/transit/page.tsx`
2. Replace bespoke cards with shadcn `<Card>` (no gradient, no blur)
3. Replace emoji headings with Lucide icons (`<Bus />`, `<Train />`)
4. Keep the data fetching + auto-refresh
5. Style status as small `<Badge variant="outline">` with `text-amber-500` / `text-emerald-500`

---

## 4. Build an approval card

> "Build an approval card component for a rental viewing booking. Show address, time, agent, rent (flag if over budget), commute, BER. Three actions: Approve / Defer / Reject."

The agent will create `apps/web/components/property/viewing-approval-card.tsx` using shadcn `Card` + `Badge` + `Button`, following the approval-card pattern in [`SKILL.md`](../SKILL.md#6-approval-card-ai-lifes-signature-pattern).

---

## 5. Quick accessibility check

> "Audit `app/dashboard/transit/page.tsx` against the a11y checklist."

The agent will work through [accessibility-checklist.md](../references/accessibility-checklist.md) and report findings.

---

## What the agent should refuse

If asked for any of these, the agent should push back and propose the new direction:

- "Add a glassmorphism card with a blue→purple gradient" → Counter-propose neutral `<Card>` with optional violet accent on the primary action.
- "Use emoji as the icon for the Transit card" → Counter-propose Lucide `<Bus />`.
- "Each domain should have its own colour palette" → Counter-propose single neutral palette + one accent.
- "Build a custom sidebar from scratch" → Counter-propose `pnpm dlx shadcn@latest add sidebar-07`.

These are all explicit forbidden patterns from the reset (see [DESIGN_DECISIONS.md](../DESIGN_DECISIONS.md#forbidden-patterns-the-reset)).

---

## Smoke tests for the skill

If the agent gives generic Tailwind advice without referencing dashboard-01, the skill isn't loaded. Try:

> "What's the foundation for AI-Life dashboards?"

Expected answer: "shadcn/ui `dashboard-01` block — installed once, every domain page slots inside its shell." If you get anything else, the skill didn't load.
