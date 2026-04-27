---
name: ux-ui-specialist
description: 'Design and build UI for AI-Life on top of shadcn/ui dashboard-01 as the canonical foundation. Aesthetic target: command centre — neutral, dense, scannable, dark-first (Linear / Vercel / Resend / Stripe family). Use for: scaffolding new domain pages inside the shell, adding KPI cards, data tables, charts, sidebars, approval cards, forms, ensuring WCAG AA. Trigger phrases: ui, ux, component, dashboard, sidebar, header, kpi, card, table, chart, form, button, input, design, layout, dark theme, geist, shadcn, dashboard-01, blocks, accessibility, a11y.'
argument-hint: 'Describe the UI surface to build (e.g., "add a Property Finder page using the dashboard-01 shell")'
---

# UX/UI Specialist — AI-Life

Design and build the AI-Life command centre UI on top of **shadcn/ui's `dashboard-01` block**. Aesthetic target: **Linear, Vercel, Resend, Stripe** — neutral, dense, scannable, dark-first, one accent colour, zero decoration.

---

## 1. Foundation: shadcn dashboard-01

**Single source of truth: https://ui.shadcn.com/blocks#dashboard-01**

This block IS the AI-Life shell. Every domain page slots inside it. Don't build app shells from scratch.

It provides:
- Collapsible sidebar (full ↔ icon-only) with section grouping
- Sticky header with breadcrumb + search + user menu
- KPI card row with delta indicators (e.g. "+12.5% trending up")
- Area chart card (Recharts, time-range toggle)
- Sortable / filterable / paginated data table with drag-to-reorder
- Tailwind v4, Radix primitives, dark mode native, WCAG AA

### Install (do this once, at the start)

```bash
cd apps/web
# 1. Init shadcn (only if not done before)
pnpm dlx shadcn@latest init
#   Style: New York
#   Base color: Neutral
#   CSS variables: yes
#   App router: yes

# 2. Install the dashboard block
pnpm dlx shadcn@latest add dashboard-01

# 3. Add any extras the block depends on (the CLI usually handles this; manual fallbacks):
pnpm dlx shadcn@latest add sidebar button card chart table dropdown-menu \
                            input label separator sheet skeleton tabs toggle \
                            tooltip badge avatar
```

The block drops files into `apps/web/components/`, `apps/web/components/ui/`, and `apps/web/app/dashboard/`. **You own them — edit freely.**

### Domain pages slot inside the shell

After installing, each AI-Life domain becomes a route under the shared shell:

```
apps/web/app/
  layout.tsx              # global (Geist fonts, providers)
  dashboard/
    layout.tsx            # SidebarProvider + AppSidebar + SiteHeader (from dashboard-01)
    page.tsx              # overview = KPIs + chart + recent table (the block default)
    transit/page.tsx      # domain page — reuses the same shell
    travel/page.tsx
    photos/page.tsx
    property/page.tsx
    finances/page.tsx
    home/page.tsx         # smart home
```

Sidebar nav items map 1:1 to these routes. Don't invent a new layout per domain.

---

## 2. Aesthetic Target

> Look like Linear's issue list. Look like Vercel's project dashboard. Look like Resend's logs page.

**Concretely:**

| Aspect | Rule |
|---|---|
| Background | Near-black neutral (shadcn `bg-background` ≈ `oklch(0.145 0 0)`) |
| Cards | Solid `bg-card` + 1px `border` — **no gradients, no backdrop-blur** |
| Accent colour | One only — Violet `#8b5cf6` (shadcn `--primary`) for primary actions, focus rings, selected states |
| Typography | Geist Sans, tight tracking (`-0.01em`), liberal `text-muted-foreground` for secondary info |
| Radii | shadcn default (`--radius: 0.625rem` ≈ 10px) — don't go bigger |
| Density | Tables, lists, sidebar are **tight** — `text-sm`, compact row height (`h-10` rows in tables) |
| Status | Small dot + short text label, never large coloured panels |
| Iconography | `lucide-react` only (already a shadcn dependency) — `size={16}` inline, `size={18}` in buttons |
| Charts | Recharts via shadcn `Chart` primitive — single accent colour, muted gridlines |

**Forbidden (this is the reset from the previous skill version):**
- ❌ `bg-gradient-to-br from-*-500/10 to-*-500/10` — no rainbow gradients per domain
- ❌ `backdrop-blur-xl` glassmorphism cards
- ❌ `rounded-3xl` (24px) — too soft, looks consumer-app, not command-centre
- ❌ Emoji prefixes in headings (`🚀 Card Title`)
- ❌ Per-domain bespoke layouts (Transit different from Travel different from Photos)
- ❌ Marketing copy ("Supercharge your life!") — show facts

---

## 3. Command Centre Principles

When building anything, ask:

1. **3-second rule** — Can the user understand this card's purpose and status in 3 seconds?
2. **Decision relevance** — Does this info help them decide or act *right now*?
3. **No hidden info** — Key status visible without hover/click.
4. **Mobile = desktop** — Same info, just stacked. Touch targets ≥ 44×44px.
5. **Motion only for state changes** — pending → approved, loading → loaded. Never decorative.

---

## 4. Standard Primitives (use these, don't reinvent)

All come from shadcn dashboard-01 / shadcn blocks. Use them everywhere for consistency.

### `<SectionCards>` — KPI Strip
4 cards across the top of any domain page. Each shows: label + big number + delta badge + one-line context.

### `<ChartAreaInteractive>` — Time-Series Card
Single card with title, time-range toggle (7d / 30d / 3m), area chart. Use for trends (commute times, expenses, viewings/week).

### `<DataTable>` — Sortable Table
Column-sortable, filterable, paginated, drag-to-reorder rows, row selection. Use for any list (saved stops, rental shortlist, transactions, photos to review).

### `<Sidebar>` (sidebar-07 variant)
Collapsible to icons, section groups (Main / Tools / Settings), user dropdown at the bottom.

### `<SiteHeader>`
Sticky top bar with breadcrumb, mobile sidebar trigger, search, theme toggle, user menu.

### Approval Card (custom — built on shadcn `Card` + `Button`)
The one AI-Life-specific primitive. See `references/approval-card.md`.

---

## 5. Tokens — Use shadcn Variables Only

Don't introduce parallel custom CSS variables. Use shadcn's tokens:

| Use case | Token | Tailwind class |
|---|---|---|
| Page background | `--background` | `bg-background` |
| Card background | `--card` | `bg-card` |
| Border | `--border` | `border-border` |
| Primary text | `--foreground` | `text-foreground` |
| Muted text | `--muted-foreground` | `text-muted-foreground` |
| Accent / primary action | `--primary` | `bg-primary text-primary-foreground` |
| Destructive | `--destructive` | `bg-destructive text-destructive-foreground` |
| Focus ring | `--ring` | `ring-ring` |
| Radius | `--radius` | `rounded-lg` (≈10px) |

Override in `apps/web/app/globals.css` only to set:
- `--primary: oklch(...)` → Violet
- Geist font variables (already done)
- Chart colours (`--chart-1..5`)

**Delete** the legacy `--bg-0..3`, `--fg-0..3`, `--accent-*`, `--approval-*` variables in `apps/web/app/globals.css` once dashboard-01 is in. They duplicate shadcn's tokens and cause drift.

---

## 6. Approval Card (AI-Life's Signature Pattern)

Approval cards are AI-Life's primary interaction. They present an action the agent wants to take, with consequences visible upfront.

```tsx
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

<Card>
  <CardHeader className="flex-row items-start justify-between space-y-0">
    <div className="space-y-1">
      <h3 className="text-base font-semibold">Book viewing — 12 Sandymount Ave</h3>
      <p className="text-sm text-muted-foreground">Sat 2 May, 14:00 — agent: DNG</p>
    </div>
    <Badge variant="outline" className="text-amber-500 border-amber-500/30">
      Pending
    </Badge>
  </CardHeader>

  <CardContent className="space-y-2 text-sm">
    <Row label="Rent" value="€2,400/mo" emphasis="warn" suffix="(€300 over budget)" />
    <Row label="Commute to work" value="22 min cycle" />
    <Row label="BER" value="C1" />
  </CardContent>

  <CardFooter className="gap-2 border-t pt-4">
    <Button size="sm">Approve</Button>
    <Button size="sm" variant="secondary">Defer</Button>
    <Button size="sm" variant="ghost" className="text-destructive">Reject</Button>
  </CardFooter>
</Card>
```

**Rules:**
- Title in `text-base font-semibold` — not 2xl bold
- Status as `Badge variant="outline"` with coloured text/border — not a giant gradient banner
- Show the **consequence** inline (`€300 over budget`) — never hide it
- Three actions: Approve / Defer / Reject — same vertical alignment, `size="sm"`
- Approve = `default` button, Defer = `secondary`, Reject = `ghost` + `text-destructive` (destructive but recoverable)

---

## 7. Workflow

When asked to build a UI surface:

1. **Check `dashboard-01` is installed.** If not, install it first.
2. **Add the route** under `apps/web/app/dashboard/<domain>/page.tsx`.
3. **Reuse the shell** from `apps/web/app/dashboard/layout.tsx` — never re-create sidebar/header.
4. **Reuse primitives** — `<SectionCards>`, `<ChartAreaInteractive>`, `<DataTable>`. Pass domain-specific data.
5. **Add the sidebar nav item** in `components/app-sidebar.tsx`.
6. **Validate accessibility** — see [accessibility-checklist.md](./references/accessibility-checklist.md).

Don't:
- Build a new layout for the domain
- Add per-domain colour gradients
- Hand-roll a sidebar or header
- Introduce new CSS variables

---

## 8. Animation

Minimal, only for state changes:
- `transition-colors duration-150` on hover / focus
- `data-[state=open]:animate-in` from shadcn (already configured) for popovers/dialogs
- Loading: `<Skeleton />` from shadcn — never spinners on full pages
- Respect `prefers-reduced-motion` (shadcn does this automatically)

Never animate: text colour, font-size, padding/margin, decorative motion.

---

## 9. Forms

- Validate **on blur + on submit** (not as-you-type)
- Use shadcn `<Form>` + `react-hook-form` + `zod` (the canonical stack)
- Required fields: `*` next to label, `aria-required="true"`
- Errors: red `text-destructive` text under field, `aria-invalid` on input
- Submit button: `<Button type="submit">` with loading state via `disabled` + `<Loader2 className="animate-spin" />`

---

## 10. Mobile

- Same info as desktop, just reflowed
- Sidebar collapses to a `<Sheet>` (shadcn) triggered from header — handled by dashboard-01 already
- Tables: shadcn `DataTable` is responsive; for very narrow screens, hide non-essential columns via `hidden md:table-cell`
- Touch targets ≥ 44×44px (shadcn `Button size="default"` is already 40px → use `h-11` if needed for primary mobile actions)

---

## 11. Accessibility (WCAG AA Floor)

shadcn primitives are accessible out of the box. You only need to:
- Add `aria-label` on icon-only buttons (`<Button size="icon" aria-label="Refresh">`)
- Use `<label htmlFor>` on every input (or shadcn `<FormLabel>`)
- Use `aria-live="polite"` for dynamic refreshing content
- Test with VoiceOver (`Cmd+F5`) before shipping

Full checklist: [accessibility-checklist.md](./references/accessibility-checklist.md).

---

## 12. When NOT to use this skill

- Backend / API design → delegate to domain specialist (Property Finder, Transit, etc.)
- Schemas / data models → not a UI concern
- Vercel deploys / CI → Vercel Guru / DevOps agents
- Auth flows → DevOps & Integration Guru
- Smart home device control logic → Smart Home Specialist (UI surface for it = this skill)

---

## Quick reference

- **Block reference:** https://ui.shadcn.com/blocks (id `dashboard-01`)
- **Components reference:** https://ui.shadcn.com/docs/components
- **Charts reference:** https://ui.shadcn.com/charts
- **Lucide icons:** https://lucide.dev
- **Local:** see [DESIGN_DECISIONS.md](./DESIGN_DECISIONS.md), [accessibility-checklist.md](./references/accessibility-checklist.md), [examples.md](./assets/examples.md)
