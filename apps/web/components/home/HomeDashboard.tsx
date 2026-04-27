"use client";

/**
 * Command-centre home for AI-Life.
 *
 * Three sections, scannable in 3 seconds:
 *  1. "What's next" — schedule advisor: when to leave for the next event.
 *  2. "Today" — today's calendar from the primary Google Calendar.
 *  3. "Travel" — next trip + estimated leave-for-airport time + pending approvals.
 *
 * APIs used (already implemented in apps/api):
 *  - GET /api/v1/schedule/when-to-leave
 *  - GET /api/v1/calendar/upcoming?days=1
 *  - GET /api/v1/trips
 *
 * Honest gap: there is no airport-aware advisor yet. The "leave for airport"
 * row shows a heuristic (depart − 3h) and is clearly labelled as an estimate.
 */

import * as React from "react";
import Link from "next/link";
import {
  ArrowRightIcon,
  CalendarClockIcon,
  CalendarIcon,
  MapPinIcon,
  PlaneTakeoffIcon,
  RefreshCwIcon,
  AlertTriangleIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

// ---------------------------------------------------------------------------
// Types — mirror the API shapes we consume.
// ---------------------------------------------------------------------------

type AdviceStatus =
  | "on_time"
  | "tight"
  | "urgent"
  | "missed"
  | "relaxed"
  | "all_day"
  | "unknown_location"
  | "no_transit"
  | "error";

interface TransitOption {
  route: string;
  mode: string;
  departure_time: string;
  arrival_time?: string;
  travel_minutes?: number;
}

interface NextEvent {
  summary: string;
  location?: string;
  start: string;
  id?: string;
}

interface ScheduleAdvice {
  advice: string;
  status: AdviceStatus;
  current_location?: string;
  next_event?: NextEvent | null;
  transit_options?: TransitOption[];
  recommended_departure?: string;
  minutes_until_depart?: number;
}

interface CalendarEvent {
  id: string;
  summary: string;
  location?: string;
  start: { dateTime?: string; date?: string };
}

interface CalendarUpcoming {
  count: number;
  events: CalendarEvent[];
}

interface Flight {
  carrier: string;
  flight_number: string;
  origin_iata: string;
  destination_iata: string;
  depart_local: string;
  arrive_local: string;
  depart_tz: string;
}

interface Trip {
  id: string;
  title: string;
  start_local: string;
  end_local: string;
  tz: string;
  flights: Flight[];
}

type ApprovalStatus = "pending" | "approved" | "rejected" | "applied";

interface TripApproval {
  trip: Trip;
  status: ApprovalStatus;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_TONE: Record<AdviceStatus, { label: string; className: string }> = {
  on_time: { label: "On time", className: "text-emerald-400 border-emerald-500/40" },
  tight: { label: "Tight", className: "text-amber-400 border-amber-500/40" },
  urgent: { label: "Leave now", className: "text-red-400 border-red-500/50" },
  missed: { label: "Missed", className: "text-red-400 border-red-500/50" },
  relaxed: { label: "Relaxed", className: "text-muted-foreground border-border" },
  all_day: { label: "All day", className: "text-muted-foreground border-border" },
  unknown_location: { label: "Check manually", className: "text-amber-400 border-amber-500/40" },
  no_transit: { label: "No transit", className: "text-amber-400 border-amber-500/40" },
  error: { label: "Error", className: "text-red-400 border-red-500/50" },
};

function fmtTime(iso?: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function fmtDayShort(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    day: "2-digit",
    month: "short",
  });
}

function eventStartIso(ev: CalendarEvent): string | undefined {
  return ev.start?.dateTime ?? ev.start?.date;
}

function isToday(iso?: string): boolean {
  if (!iso) return false;
  const d = new Date(iso);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function HomeDashboard() {
  const [advice, setAdvice] = React.useState<ScheduleAdvice | null>(null);
  const [adviceError, setAdviceError] = React.useState<string | null>(null);
  const [adviceLoading, setAdviceLoading] = React.useState(true);

  const [today, setToday] = React.useState<CalendarEvent[] | null>(null);
  const [todayError, setTodayError] = React.useState<string | null>(null);
  const [todayLoading, setTodayLoading] = React.useState(true);

  const [trips, setTrips] = React.useState<TripApproval[] | null>(null);
  const [tripsError, setTripsError] = React.useState<string | null>(null);
  const [tripsLoading, setTripsLoading] = React.useState(true);

  const [refreshing, setRefreshing] = React.useState(false);

  const loadAll = React.useCallback(async () => {
    setRefreshing(true);
    const results = await Promise.allSettled([
      fetch("/api/v1/schedule/when-to-leave").then((r) => {
        if (!r.ok) throw new Error(`schedule ${r.status}`);
        return r.json() as Promise<ScheduleAdvice>;
      }),
      fetch("/api/v1/calendar/upcoming?days=1").then((r) => {
        if (!r.ok) throw new Error(`calendar ${r.status}`);
        return r.json() as Promise<CalendarUpcoming>;
      }),
      fetch("/api/v1/trips").then((r) => {
        if (!r.ok) throw new Error(`trips ${r.status}`);
        return r.json() as Promise<TripApproval[]>;
      }),
    ]);

    const [a, c, t] = results;
    if (a.status === "fulfilled") {
      setAdvice(a.value);
      setAdviceError(null);
    } else {
      setAdviceError(a.reason?.message ?? "failed");
    }
    setAdviceLoading(false);

    if (c.status === "fulfilled") {
      setToday(c.value.events.filter((ev) => isToday(eventStartIso(ev))));
      setTodayError(null);
    } else {
      setTodayError(c.reason?.message ?? "failed");
    }
    setTodayLoading(false);

    if (t.status === "fulfilled") {
      setTrips(t.value);
      setTripsError(null);
    } else {
      setTripsError(t.reason?.message ?? "failed");
    }
    setTripsLoading(false);

    setRefreshing(false);
  }, []);

  React.useEffect(() => {
    loadAll();
    // Auto-refresh every 60s so "minutes until depart" stays fresh.
    const id = window.setInterval(loadAll, 60_000);
    return () => window.clearInterval(id);
  }, [loadAll]);

  return (
    <div className="flex flex-col gap-4 px-4 py-4 md:gap-6 md:py-6 lg:px-6">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-heading text-xl font-semibold tracking-tight">
            Today
          </h1>
          <p className="text-sm text-muted-foreground">
            What needs your attention right now.
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={loadAll}
          disabled={refreshing}
          aria-label="Refresh"
        >
          <RefreshCwIcon className={refreshing ? "animate-spin" : undefined} />
          Refresh
        </Button>
      </header>

      <NextMoveCard
        advice={advice}
        loading={adviceLoading}
        error={adviceError}
      />

      <div className="grid grid-cols-1 gap-4 md:gap-6 lg:grid-cols-2">
        <TodayCard
          events={today}
          loading={todayLoading}
          error={todayError}
        />
        <TravelCard
          trips={trips}
          loading={tripsLoading}
          error={tripsError}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// "What's next" — schedule advisor hero
// ---------------------------------------------------------------------------

function NextMoveCard({
  advice,
  loading,
  error,
}: {
  advice: ScheduleAdvice | null;
  loading: boolean;
  error: string | null;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div className="flex items-center gap-2">
          <CalendarClockIcon className="size-4 text-muted-foreground" />
          <CardTitle>What&rsquo;s next</CardTitle>
        </div>
        {advice ? (
          <Badge
            variant="outline"
            className={STATUS_TONE[advice.status].className}
          >
            {STATUS_TONE[advice.status].label}
          </Badge>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-4 px-4">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-7 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : error ? (
          <ErrorRow message={`Schedule advisor unreachable: ${error}`} />
        ) : advice ? (
          <NextMoveBody advice={advice} />
        ) : null}
      </CardContent>
    </Card>
  );
}

function NextMoveBody({ advice }: { advice: ScheduleAdvice }) {
  const ev = advice.next_event;
  const minutes = advice.minutes_until_depart;
  const leaveAt = advice.recommended_departure;
  const top = advice.transit_options?.[0];

  return (
    <>
      <div className="flex items-baseline gap-3">
        {typeof minutes === "number" && minutes >= 0 ? (
          <>
            <span className="font-heading text-3xl font-semibold tabular-nums">
              {minutes}
            </span>
            <span className="text-sm text-muted-foreground">
              min until you should leave
            </span>
          </>
        ) : (
          <span className="text-base font-medium">{advice.advice}</span>
        )}
      </div>

      {ev ? (
        <div className="text-sm text-muted-foreground">
          <span className="text-foreground">{ev.summary}</span>
          {ev.start ? <> · {fmtTime(ev.start)}</> : null}
          {ev.location ? (
            <>
              {" "}
              ·{" "}
              <span className="inline-flex items-center gap-1">
                <MapPinIcon className="size-3.5" />
                {ev.location}
              </span>
            </>
          ) : null}
        </div>
      ) : null}

      {top || leaveAt ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
          {leaveAt ? (
            <span>
              <span className="text-muted-foreground">Leave at </span>
              <span className="font-medium tabular-nums">
                {fmtTime(leaveAt)}
              </span>
            </span>
          ) : null}
          {top ? (
            <span>
              <span className="text-muted-foreground">Catch </span>
              <span className="font-medium uppercase">{top.route}</span>
              <span className="text-muted-foreground">
                {" "}
                ({top.mode}) at {top.departure_time}
              </span>
            </span>
          ) : null}
        </div>
      ) : null}

      <Separator />
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{advice.advice}</span>
        <Link
          href="/dashboard/transit"
          className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
        >
          Transit detail <ArrowRightIcon className="size-3" />
        </Link>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// "Today" — calendar
// ---------------------------------------------------------------------------

function TodayCard({
  events,
  loading,
  error,
}: {
  events: CalendarEvent[] | null;
  loading: boolean;
  error: string | null;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2 space-y-0">
        <CalendarIcon className="size-4 text-muted-foreground" />
        <CardTitle>Today&rsquo;s calendar</CardTitle>
      </CardHeader>
      <CardContent className="px-4">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-5/6" />
            <Skeleton className="h-5 w-4/6" />
          </div>
        ) : error ? (
          <ErrorRow message={`Calendar unreachable: ${error}`} />
        ) : !events || events.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nothing on the calendar today.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {events.map((ev) => {
              const start = eventStartIso(ev);
              const allDay = !ev.start.dateTime;
              return (
                <li
                  key={ev.id}
                  className="flex items-baseline gap-3 py-2 text-sm first:pt-0 last:pb-0"
                >
                  <span className="w-12 shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                    {allDay ? "all day" : fmtTime(start)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-foreground">
                      {ev.summary || "(no title)"}
                    </div>
                    {ev.location ? (
                      <div className="truncate text-xs text-muted-foreground">
                        {ev.location}
                      </div>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// "Travel" — next trip + airport leave-by + pending approvals
// ---------------------------------------------------------------------------

interface AirportAdvice {
  trip_id: string | null;
  leave_by_local: string;
  depart_local: string;
  origin_iata: string;
  destination_iata: string;
  confidence: "estimate" | "live";
  data_sources: string[];
  notes: string[];
  breakdown: {
    flight_category: "short_haul" | "long_haul";
    mode: string;
    is_peak: boolean;
    check_in_close_min: number;
    security_min: number;
    transfer_to_gate_min: number;
    travel_time_min: number;
    personal_buffer_min: number;
    total_offset_min: number;
  };
}

function TravelCard({
  trips,
  loading,
  error,
}: {
  trips: TripApproval[] | null;
  loading: boolean;
  error: string | null;
}) {
  // Next upcoming trip (any status), preferring applied/approved trips with a flight.
  const now = Date.now();
  const upcoming = (trips ?? [])
    .filter((a) => new Date(a.trip.start_local).getTime() >= now - 86_400_000)
    .sort(
      (a, b) =>
        new Date(a.trip.start_local).getTime() -
        new Date(b.trip.start_local).getTime(),
    );
  const next = upcoming[0];
  const pendingCount = (trips ?? []).filter((a) => a.status === "pending").length;

  const [airport, setAirport] = React.useState<AirportAdvice | null>(null);
  const [airportError, setAirportError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!next || !next.trip.flights?.length) {
      setAirport(null);
      return;
    }
    const ctrl = new AbortController();
    fetch(
      `/api/v1/schedule/leave-for-airport?trip_id=${encodeURIComponent(
        next.trip.id,
      )}&mode=taxi`,
      { signal: ctrl.signal },
    )
      .then((r) => {
        if (!r.ok) throw new Error(`airport advisor ${r.status}`);
        return r.json() as Promise<AirportAdvice>;
      })
      .then((data) => {
        setAirport(data);
        setAirportError(null);
      })
      .catch((e: unknown) => {
        if (e instanceof Error && e.name !== "AbortError") {
          setAirportError(e.message);
        }
      });
    return () => ctrl.abort();
  }, [next?.trip.id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
        <div className="flex items-center gap-2">
          <PlaneTakeoffIcon className="size-4 text-muted-foreground" />
          <CardTitle>Travel</CardTitle>
        </div>
        {pendingCount > 0 ? (
          <Badge
            variant="outline"
            className="border-amber-500/40 text-amber-400"
          >
            {pendingCount} pending
          </Badge>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-3 px-4">
        {loading ? (
          <Skeleton className="h-16 w-full" />
        ) : error ? (
          <ErrorRow message={`Trips unreachable: ${error}`} />
        ) : !next ? (
          <p className="text-sm text-muted-foreground">No upcoming trips.</p>
        ) : (
          <NextTripBody
            approval={next}
            airport={airport}
            airportError={airportError}
          />
        )}

        <Separator />
        <Link
          href="/dashboard/travel"
          className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
        >
          All trips & approvals <ArrowRightIcon className="size-3" />
        </Link>
      </CardContent>
    </Card>
  );
}

function NextTripBody({
  approval,
  airport,
  airportError,
}: {
  approval: TripApproval;
  airport: AirportAdvice | null;
  airportError: string | null;
}) {
  const t = approval.trip;
  const firstFlight = t.flights?.[0];

  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-medium">{t.title}</span>
        <span className="text-xs text-muted-foreground tabular-nums">
          {fmtDayShort(t.start_local)}
        </span>
      </div>

      {firstFlight ? (
        <div className="text-xs text-muted-foreground">
          <span className="font-mono uppercase text-foreground">
            {firstFlight.carrier}
            {firstFlight.flight_number}
          </span>{" "}
          · {firstFlight.origin_iata} → {firstFlight.destination_iata} · depart{" "}
          <span className="tabular-nums text-foreground">
            {fmtTime(firstFlight.depart_local)}
          </span>
        </div>
      ) : null}

      {airportError ? (
        <ErrorRow message={`Airport advisor: ${airportError}`} />
      ) : airport ? (
        <AirportLeaveBy advice={airport} />
      ) : firstFlight ? (
        <Skeleton className="h-14 w-full" />
      ) : null}
    </div>
  );
}

function AirportLeaveBy({ advice }: { advice: AirportAdvice }) {
  const b = advice.breakdown;
  const confidenceTone =
    advice.confidence === "live"
      ? "text-emerald-400 border-emerald-500/40"
      : "text-amber-400 border-amber-500/40";

  return (
    <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs text-muted-foreground">Leave for airport</span>
        <span className="font-mono text-sm tabular-nums">
          {fmtDayShort(advice.leave_by_local)} {fmtTime(advice.leave_by_local)}
        </span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-muted-foreground">
        <Badge
          variant="outline"
          className={`h-4 px-1 text-[10px] ${confidenceTone}`}
        >
          {advice.confidence}
        </Badge>
        <span>
          {b.flight_category === "long_haul" ? "Long-haul" : "Short-haul"} ·{" "}
          {b.mode} · {b.is_peak ? "peak" : "off-peak"}
        </span>
      </div>
      <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 font-mono text-[11px] tabular-nums text-muted-foreground sm:grid-cols-3">
        <span>travel {b.travel_time_min}m</span>
        <span>check-in {b.check_in_close_min}m</span>
        <span>security {b.security_min}m</span>
        <span>gate {b.transfer_to_gate_min}m</span>
        <span>buffer {b.personal_buffer_min}m</span>
        <span className="text-foreground">total {b.total_offset_min}m</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

function ErrorRow({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 text-xs text-amber-400">
      <AlertTriangleIcon className="mt-0.5 size-3.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
