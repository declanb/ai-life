# AI-Life: Personal Agentic Assistant Brainstorm

This document captures the foundation for your **AI-Life** project—a personal, agentic assistant focused on automating your physical environment and streamlining your personal life admin, strictly separated from work, finances, and day-to-day messaging.

---

## 1. Core Pillars of "AI-Life"

Based on your prompt, we are dividing the assistant's responsibilities into two major categories: **The Physical Layer** (Smart Home) and **The Digital Layer** (Life Admin & Time).

### The Physical Layer (Smart Home & IoT)
*Goal: Move from "rules-based" automation to "context-aware" agentic behavior.*

*   **Adaptive Lighting & Blinds:** Instead of a rigid schedule (e.g., "blinds close at 8 PM"), the agent checks your personal calendar and the weather. 
    *   *Example:* If you are returning home late, it leaves the porch light on and closes the blinds. If you are watching a movie (calendar event or TV status), it dims the lights and drops the blinds automatically.
*   **Intelligent Camera Management:**
    *   *Example:* The agent arms the cameras when it detects your phone has left the geofence, but it suppresses non-urgent notifications if it knows you're in a personal deep-focus or relaxation block.

### The Digital Layer (Life Admin & Time)
*Goal: Proactive management of the mundane so you only deal with high-level approvals.*

*   **The Renewal Engine (Subscriptions & Insurance):**
    *   The agent monitors your personal email for upcoming renewals (car insurance, home insurance, software subscriptions, gym memberships).
    *   *Agentic workflow:* When a renewal approaches, it automatically searches the web for better quotes, compares them to your current rate, and presents a summary: *"Your insurance is renewing for £400. I found a quote for £320. Should I draft a cancellation email to your current provider?"*
*   **Inbox Sentinel (Personal Email Triage):**
    *   Since responding to personal messages/WhatsApp is out of scope, the agent acts as an email bouncer.
    *   It reads incoming personal emails, archives spam/newsletters, and extracts actionable items.
    *   *Example:* It sees an email about a family event, extracts the date, and proposes a calendar invite.
*   **Schedule Orchestration:**
    *   Managing your personal calendar by blocking out necessary personal time, travel time, and unstructured relaxation time.
    *   *Example:* If an email confirms a flight or train, the agent adds it to your calendar *and* adds the buffer travel time.

---

## 2. Guardrails & Boundaries

### 2.1 Hard scope rule: PERSONAL ONLY
**AI-Life is a personal-life system. It does not connect to, read from, write to, or automate any work or employer/client account — ever.**

*   ❌ **EY** — no email, calendar, Teams, OneDrive, SharePoint, Concur (as a work tool), or any EY-issued account.
*   ❌ **Airnova** — no Airnova accounts, data, or systems of any kind.
*   ❌ Any other current or future employer / client work account.
*   ❌ No work credentials, OAuth tokens, or API keys are ever stored in this repo or its services.

**The single allowed overlap — work *trips*, read-only, one-way, into personal:**
Work **travel itineraries** (flights, trains, hotels, dates, destinations) are in scope as personal-life context — the user is physically away, the home needs to react (vacation mode, lights, climate), and the family needs visibility. They get mirrored into the personal calendar (e.g. an "AI-Life — Travel" Google Calendar) and feed Home Assistant routines.

Constraints on this overlap:
*   Source must be a **personal channel** — a forwarded confirmation email landing in personal Gmail, a personal Concur export the user drops in, or similar. Never a direct OAuth into a work system.
*   **Trip metadata only** — dates, locations, transport, accommodation. Not work meeting subjects, attendees, agendas, documents, or any work content beyond what's needed to know "user is in city X from date A to date B".
*   **One-way**, into personal. No data ever flows back to any work system.

### 2.2 Automation posture: maximum autonomy with revertible side-effects
The user wants to automate as much as possible. Default policy:

*   **Auto-execute (no approval card):** read-only ingestion, summarisation, classification, calendar mirroring, photo organisation, renewal *detection*, and pre-blessed Home Assistant routines (lights, climate, scenes, vacation/away mode).
*   **Approval Card required (irreversible / external side-effect):** cancelling subscriptions, sending email on the user's behalf, arming/disarming security, unlocking doors, moving money, deleting photos or files, or **any first-time action against a new vendor**.
*   **Always:** server-side audit log of what ran, when, why, and which approval (if any) authorised it.

### 2.3 Other excluded domains
*   ❌ Financial *transactions* / active bill payment (read-only analysis & renewal detection are fine).
*   ❌ Auto-replying to WhatsApp, iMessage, or personal texts.

### 2.4 Shopping — propose-only, never auto-checkout
**Shopping (groceries + non-grocery) is in scope as propose-only automation.** Specialist agents (`Groceries Shopper`, `Personal Shopper`) build baskets, compare retailers, apply loyalty/offers, and surface ready-to-approve proposals via approval cards. **The user always places the actual order** — no auto-checkout, no storing payment credentials.

*   ✅ In scope: basket building, price comparison, restock detection, gift planning, delivery-slot strategy, loyalty optimisation.
*   ❌ Out of scope: placing/amending/cancelling real orders, storing passwords/payment details, meal *cooking* (meal planning that feeds a grocery basket is fine).

---

## 3. Potential Tech Stack & Integrations

To build an agentic system that can interact with both the physical and digital world:

1.  **Orchestration / Brain:** 
    *   A bespoke Node.js/Python backend using an LLM as the reasoning engine for parsing emails and making decisions (e.g., using a framework like LangChain or AutoGen).
2.  **Physical World Interface:** 
    *   **Home Assistant (Local IoT):** The agent connects to a local Home Assistant instance via API to read camera states and trigger lights/blinds securely without exposing your home directly to the web.
3.  **Digital World Interface:** 
    *   **Google Workspace / Outlook APIs:** For read-only access to emails and read/write access to your calendar.
    *   **Web Scraping / Search Tools:** For the Renewal Engine to check competitor pricing.
4.  **UI / Dashboard (Optional but recommended):**
    *   A sleek, dark-mode Next.js dashboard where the agent leaves "Approval Cards" (e.g., "Approve Calendar Event", "Approve Renewal Switch") for you to review and clear out once a day.

---

## Next Steps for Brainstorming

Which area excites you the most to tackle first? 
1.  **The Context-Aware Home** (Hooking up the physical devices to an AI brain).
2.  **The Renewal/Admin Engine** (Setting up email parsing and proactive alerting).
3.  **The Schedule Orchestrator** (Getting the personal calendar automated).
