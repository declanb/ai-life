'use client';

import React, { useEffect, useState } from 'react';
import { Calendar, MapPin, Clock, Euro, ExternalLink, ShoppingBag, Utensils, Landmark } from 'lucide-react';

interface ShoppingRecommendation {
  title: string;
  category: string;
  description: string;
  price_estimate: string | null;
  price_level: string;
  location: string;
  address: string | null;
  opening_hours: string | null;
  distance_from_hotel: string | null;
  url: string | null;
  confidence_score: number;
  reasoning: string;
}

interface ActivityRecommendation {
  title: string;
  category: string;
  description: string;
  price_estimate: string | null;
  price_level: string;
  duration: string;
  location: string;
  address: string | null;
  distance_from_hotel: string | null;
  url: string | null;
  booking_required: boolean;
  best_time: string | null;
  confidence_score: number;
  reasoning: string;
}

interface FreeDayContext {
  location: string;
  trip_id: string | null;
  trip_title: string | null;
  hotel_name: string | null;
  hotel_address: string | null;
  date: string;
  time_available: string;
  weather: string | null;
  local_time: string;
}

interface FreeDayPlan {
  context: FreeDayContext;
  shopping_recommendations: ShoppingRecommendation[];
  activity_recommendations: ActivityRecommendation[];
  generated_at: string;
}

const PRICE_LEVEL_LABELS: Record<string, string> = {
  budget: '€',
  moderate: '€€',
  premium: '€€€',
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  shopping: <ShoppingBag size={16} />,
  activity: <Landmark size={16} />,
  dining: <Utensils size={16} />,
  food: <Utensils size={16} />,
  sightseeing: <Landmark size={16} />,
};

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { 
    weekday: 'long',
    day: '2-digit', 
    month: 'long',
    year: 'numeric' 
  });
}

export default function FreeDayPlanner() {
  const [plan, setPlan] = useState<FreeDayPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // For demo: hardcoded to Munich
  // In production: detect from current trip + calendar API
  const [location, setLocation] = useState('Munich');
  const [timeAvailable, setTimeAvailable] = useState('All day');

  useEffect(() => {
    fetchPlan();
  }, [location, timeAvailable]);

  const fetchPlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        location,
        time_available: timeAvailable,
      });
      const res = await fetch(`/api/v1/free-days/plan?${params}`);
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `Failed to load plan (${res.status})`);
      }
      setPlan(await res.json());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <section className="px-6 py-10 max-w-6xl mx-auto">
        <p className="text-muted-foreground">Loading your free day plan...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="px-6 py-10 max-w-6xl mx-auto">
        <div className="rounded border border-destructive/40 bg-destructive/10 p-3 text-destructive text-sm">
          {error}
        </div>
      </section>
    );
  }

  if (!plan) {
    return (
      <section className="px-6 py-10 max-w-6xl mx-auto">
        <p className="text-muted-foreground">No plan available</p>
      </section>
    );
  }

  const ctx = plan.context;

  return (
    <section className="px-6 py-10 max-w-6xl mx-auto space-y-8">
      {/* Context header */}
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <MapPin size={20} className="text-primary" />
          <h2 className="text-2xl font-semibold tracking-tight">{ctx.location}</h2>
          <span className="text-xs text-muted-foreground px-2 py-1 rounded-md bg-primary/10 border border-primary/20">
            Corporate card-friendly
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Calendar size={14} />
            <span>{fmtDate(ctx.date)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Clock size={14} />
            <span>{ctx.time_available}</span>
          </div>
          {ctx.hotel_name && (
            <div className="flex items-center gap-1.5">
              <span>Staying at</span>
              <span className="text-foreground">{ctx.hotel_name}</span>
            </div>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-3">
          Premium experiences + best-value shopping. All transport via Uber Black. One-tap approve to add to calendar.
        </p>
      </header>

      {/* Shopping recommendations */}
      {plan.shopping_recommendations.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <ShoppingBag size={18} className="text-primary" />
            <h3 className="text-lg font-semibold">Shopping</h3>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {plan.shopping_recommendations.map((rec, i) => (
              <ShoppingCard key={i} rec={rec} />
            ))}
          </div>
        </div>
      )}

      {/* Activity recommendations */}
      {plan.activity_recommendations.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Landmark size={18} className="text-primary" />
            <h3 className="text-lg font-semibold">Activities</h3>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {plan.activity_recommendations.map((rec, i) => (
              <ActivityCard key={i} rec={rec} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function ShoppingCard({ rec }: { rec: ShoppingRecommendation }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 flex-1">
          <h4 className="text-base font-semibold">{rec.title}</h4>
          <p className="text-xs text-muted-foreground uppercase tracking-wider">
            {rec.category.replace('_', ' ')}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {rec.price_estimate && (
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {rec.price_estimate}
            </span>
          )}
          <span className="text-xs font-medium text-primary">
            {PRICE_LEVEL_LABELS[rec.price_level] || rec.price_level}
          </span>
        </div>
      </div>

      <p className="text-sm">{rec.description}</p>

      <div className="space-y-1.5 text-xs text-muted-foreground">
        <div className="flex items-start gap-2">
          <MapPin size={12} className="mt-0.5 shrink-0" />
          <div>
            <div className="text-foreground">{rec.location}</div>
            {rec.distance_from_hotel && <div>{rec.distance_from_hotel}</div>}
          </div>
        </div>
        {rec.opening_hours && (
          <div className="flex items-start gap-2">
            <Clock size={12} className="mt-0.5 shrink-0" />
            <span>{rec.opening_hours}</span>
          </div>
        )}
      </div>

      <div className="pt-2 border-t">
        <p className="text-xs text-muted-foreground italic">{rec.reasoning}</p>
      </div>

      <div className="flex gap-2 pt-2">
        <button className="flex-1 px-3 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 font-medium">
          Add to plan
        </button>
        {rec.url && (
          <a
            href={rec.url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-2 text-sm rounded-lg border border-border bg-background hover:bg-muted inline-flex items-center gap-1.5"
          >
            <ExternalLink size={14} />
          </a>
        )}
      </div>
    </div>
  );
}

function ActivityCard({ rec }: { rec: ActivityRecommendation }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 flex-1">
          <h4 className="text-base font-semibold">{rec.title}</h4>
          <p className="text-xs text-muted-foreground uppercase tracking-wider">
            {rec.category.replace('_', ' ')} · {rec.duration}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {rec.price_estimate && (
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {rec.price_estimate}
            </span>
          )}
          <span className="text-xs font-medium text-primary">
            {PRICE_LEVEL_LABELS[rec.price_level] || rec.price_level}
          </span>
        </div>
      </div>

      <p className="text-sm">{rec.description}</p>

      <div className="space-y-1.5 text-xs text-muted-foreground">
        <div className="flex items-start gap-2">
          <MapPin size={12} className="mt-0.5 shrink-0" />
          <div>
            <div className="text-foreground">{rec.location}</div>
            {rec.distance_from_hotel && <div>{rec.distance_from_hotel}</div>}
          </div>
        </div>
        {rec.best_time && (
          <div className="flex items-start gap-2">
            <Clock size={12} className="mt-0.5 shrink-0" />
            <span>{rec.best_time}</span>
          </div>
        )}
        {rec.booking_required && (
          <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[11px]">
            Booking required
          </div>
        )}
      </div>

      <div className="pt-2 border-t">
        <p className="text-xs text-muted-foreground italic">{rec.reasoning}</p>
      </div>

      <div className="flex gap-2 pt-2">
        <button className="flex-1 px-3 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 font-medium">
          Add to calendar
        </button>
        {rec.url && (
          <a
            href={rec.url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-2 text-sm rounded-lg border border-border bg-background hover:bg-muted inline-flex items-center gap-1.5"
          >
            <ExternalLink size={14} />
          </a>
        )}
      </div>
    </div>
  );
}
