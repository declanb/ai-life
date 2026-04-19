'use client';

import React, { useCallback, useEffect, useState } from 'react';

interface Flight {
  carrier: string;
  flight_number: string;
  origin_iata: string;
  destination_iata: string;
  depart_local: string;
  arrive_local: string;
  depart_tz: string;
  arrive_tz: string;
  confirmation_code?: string | null;
}

interface Hotel {
  name: string;
  address?: string | null;
  check_in_local: string;
  check_out_local: string;
  tz: string;
  confirmation_code?: string | null;
}

interface Trip {
  id: string;
  title: string;
  start_local: string;
  end_local: string;
  tz: string;
  flights: Flight[];
  hotels: Hotel[];
  source: string;
  notes?: string | null;
}

type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'applied';

interface TripApproval {
  trip: Trip;
  status: ApprovalStatus;
  created_at: string;
  applied_at?: string | null;
  google_calendar_id?: string | null;
  event_ids: string[];
}

const STATUS_STYLE: Record<ApprovalStatus, string> = {
  pending: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  approved: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
  applied: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  rejected: 'bg-zinc-500/15 text-zinc-400 border-zinc-500/30',
};

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function fmtDay(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function TravelDashboard() {
  const [trips, setTrips] = useState<TripApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const fetchTrips = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/trips');
      if (!res.ok) throw new Error(`Failed to load trips (${res.status})`);
      setTrips(await res.json());
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTrips();
  }, [fetchTrips]);

  const act = async (
    tripId: string,
    action: 'approve' | 'reject' | 'revert',
  ) => {
    const method = action === 'revert' ? 'DELETE' : 'POST';
    const path =
      action === 'revert'
        ? `/api/v1/trips/${tripId}`
        : `/api/v1/trips/${tripId}/${action}`;
    if (action === 'revert' && !confirm('Remove all calendar events for this trip?')) return;
    setBusyId(tripId);
    try {
      const res = await fetch(path, { method });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `${action} failed`);
      }
      await fetchTrips();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="px-6 py-10 max-w-5xl mx-auto">
      <header className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight">Travel Sync</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Trip approval cards. Approving writes events to your
          <span className="text-zinc-200"> AI-Life — Travel </span>
          Google Calendar. Nothing syncs without your explicit approval.
        </p>
      </header>

      {loading && <p className="text-zinc-500">Loading…</p>}
      {error && (
        <div className="rounded border border-red-500/40 bg-red-500/10 p-3 text-red-300 text-sm">
          {error}
        </div>
      )}

      {!loading && !error && trips.length === 0 && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-6 text-center text-zinc-500">
          No trips yet. POST a trip to <code className="text-zinc-300">/api/v1/trips</code> to
          create an approval card.
        </div>
      )}

      <ul className="space-y-4">
        {trips.map((a) => {
          const t = a.trip;
          const disabled = busyId === t.id;
          return (
            <li
              key={t.id}
              className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-medium">{t.title}</h3>
                    <span
                      className={`text-[11px] uppercase tracking-wider px-2 py-0.5 rounded border ${STATUS_STYLE[a.status]}`}
                    >
                      {a.status}
                    </span>
                    <span className="text-[11px] text-zinc-500">source: {t.source}</span>
                  </div>
                  <p className="text-sm text-zinc-400 mt-1">
                    {fmtDay(t.start_local)} — {fmtDay(t.end_local)}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  {a.status === 'pending' && (
                    <>
                      <button
                        onClick={() => act(t.id, 'approve')}
                        disabled={disabled}
                        className="px-3 py-1.5 text-sm rounded bg-emerald-500/20 text-emerald-200 border border-emerald-500/40 hover:bg-emerald-500/30 disabled:opacity-50"
                      >
                        Approve & sync
                      </button>
                      <button
                        onClick={() => act(t.id, 'reject')}
                        disabled={disabled}
                        className="px-3 py-1.5 text-sm rounded bg-zinc-800 text-zinc-300 border border-zinc-700 hover:bg-zinc-700 disabled:opacity-50"
                      >
                        Reject
                      </button>
                    </>
                  )}
                  {a.status === 'applied' && (
                    <button
                      onClick={() => act(t.id, 'revert')}
                      disabled={disabled}
                      className="px-3 py-1.5 text-sm rounded bg-red-500/15 text-red-300 border border-red-500/40 hover:bg-red-500/25 disabled:opacity-50"
                    >
                      Revert
                    </button>
                  )}
                </div>
              </div>

              {t.flights.length > 0 && (
                <div className="mt-4">
                  <p className="text-[11px] uppercase tracking-wider text-zinc-500 mb-2">
                    Flights
                  </p>
                  <ul className="space-y-1.5 text-sm">
                    {t.flights.map((f, i) => (
                      <li
                        key={i}
                        className="flex items-center gap-3 text-zinc-300"
                      >
                        <span className="font-mono text-zinc-400">
                          {f.carrier}
                          {f.flight_number}
                        </span>
                        <span>
                          {f.origin_iata} → {f.destination_iata}
                        </span>
                        <span className="text-zinc-500">
                          {fmtDate(f.depart_local)} → {fmtDate(f.arrive_local)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {t.hotels.length > 0 && (
                <div className="mt-4">
                  <p className="text-[11px] uppercase tracking-wider text-zinc-500 mb-2">
                    Hotels
                  </p>
                  <ul className="space-y-1.5 text-sm">
                    {t.hotels.map((h, i) => (
                      <li key={i} className="text-zinc-300">
                        <span className="font-medium">{h.name}</span>
                        <span className="text-zinc-500 ml-2">
                          {fmtDay(h.check_in_local)} → {fmtDay(h.check_out_local)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
