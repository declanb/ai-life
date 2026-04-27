# UX/UI Specialist Skill

Build the AI-Life command centre on top of **shadcn/ui `dashboard-01`**.

Aesthetic target: **Linear / Vercel / Resend / Stripe** — neutral, dense, dark-first, one accent.

## How to use this skill

The skill auto-loads on UI/UX requests. Trigger it explicitly with phrases like:

```
"add a Property Finder page using the dashboard-01 shell"
"build an approval card for a rental viewing"
"add a KPI strip to the Finances page"
"add Transit to the sidebar nav"
"review this component for a11y"
```

The agent will:
1. Read [SKILL.md](./SKILL.md) for current rules
2. Confirm dashboard-01 is installed (or install it)
3. Slot the new surface inside the shared shell
4. Reuse `SectionCards` / `ChartAreaInteractive` / `DataTable` primitives
5. Validate against [accessibility-checklist.md](./references/accessibility-checklist.md)

## File map

```
.github/skills/ux-ui-specialist/
├── README.md                 ← you are here
├── SKILL.md                  ← canonical rules (start here)
├── DESIGN_DECISIONS.md       ← why this approach, what's banned
├── references/
│   └── accessibility-checklist.md
└── assets/
    └── examples.md           ← prompt examples + expected behaviour
```

## Bootstrap (run once, when you're ready)

```bash
cd apps/web
pnpm dlx shadcn@latest init        # New York / Neutral / CSS vars yes / App router yes
pnpm dlx shadcn@latest add dashboard-01
```

Then delete the legacy `--bg-0..3`, `--fg-0..3`, `--accent-*` blocks from `apps/web/app/globals.css` and let shadcn tokens take over. Only override `--primary` to violet (`oklch(0.606 0.25 292.717)`) and keep the Geist font variables.

## Forbidden (this is the reset)

- ❌ Rainbow gradients per domain (`from-blue-500/10 to-purple-500/10`)
- ❌ `backdrop-blur-xl` glassmorphism
- ❌ `rounded-3xl`, emoji-headed cards, hand-rolled layouts
- ❌ Parallel custom CSS variables alongside shadcn's

## When to use

UI / UX / component / dashboard / sidebar / table / chart / form / accessibility work in `apps/web`.

## When NOT to use

Backend, schemas, deploys, auth, smart-home device logic — delegate to the relevant specialist agent.
