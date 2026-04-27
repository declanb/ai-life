'use client';

import React, { useEffect, useState } from 'react';

interface Listing {
    canonical_id: string;
    source: string;
    source_url: string;
    area_routing_key: string;
    address_rough: string;
    beds: number;
    baths: number;
    rent_eur: number;
    bills_included: boolean;
    estimated_bills_eur: number;
    parking_available: boolean;
    furnished: boolean;
    ber_rating: string | null;
    floor_area_sqm: number | null;
    lease_length_months: number | null;
    available_from: string | null;
    agent_name: string | null;
    agent_psra: string | null;
    photos_count: number;
    has_floor_plan: boolean;
    days_on_market: number | null;
    image_url: string | null;
}

interface ListingScore {
    commute_minutes: number | null;
    buy_overlap_score: number;
    listing_quality_score: number;
    mortgage_area_sanity: string;
    rpz_flag: boolean;
    affordability_verdict: string | null;
    affordability_note: string | null;
}

interface RankedListing {
    listing: Listing;
    scores: ListingScore;
    rank: number;
    why_this: string;
    deal_breakers_passed: string[];
}

interface ReadinessSnapshot {
    deposit_runway_months: number | null;
    aip_action: string;
    scheme_recommendation: string;
    next_concrete_action: string;
    not_regulated_advice_note: string;
}

interface SourceStatus {
    name: string;
    ok: boolean;
    count: number;
    note: string;
}

interface ShortlistResponse {
    rental_spec: { area_routing_keys: string[]; max_rent_eur: number; move_in_date: string };
    ranked_listings: RankedListing[];
    recommended_pick: RankedListing | null;
    readiness_snapshot: ReadinessSnapshot | null;
    sources: SourceStatus[];
    spec_notes: string;
    generated_at: string;
}

interface DiscoveriesResponse {
    last_run_at: string | null;
    recent_new_ids: string[];
    events: Array<{ at: string; new_ids: string[]; gone_ids: string[]; total_listings: number }>;
}

const sourceLabel = (s: string) => {
    const map: Record<string, string> = {
        daft: 'Daft.ie',
        myhome: 'MyHome.ie',
        'rent.ie': 'Rent.ie',
        sherryfitz: 'Sherry FitzGerald',
        dng: 'DNG',
        savills: 'Savills',
        knightfrank: 'Knight Frank',
        hooke_macdonald: 'Hooke & MacDonald',
        lisney: 'Lisney',
        fixtures: 'Demo data',
    };
    return map[s] || s;
};

const verdictColor = (v: string | null) => {
    if (v === 'green') return '#22c55e';
    if (v === 'amber') return '#f59e0b';
    if (v === 'red') return '#ef4444';
    return 'var(--fg-2)';
};

export default function PropertyFinderDashboard() {
    const [data, setData] = useState<ShortlistResponse | null>(null);
    const [discoveries, setDiscoveries] = useState<DiscoveriesResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [pastedUrls, setPastedUrls] = useState<string[]>([]);
    const [newUrls, setNewUrls] = useState('');
    const [refreshing, setRefreshing] = useState(false);

    const fetchShortlist = async () => {
        setLoading(true);
        setError(null);
        try {
            const r = await fetch('/api/v1/property-finder/shortlist');
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const json = await r.json();
            setData(json);
        } catch (e: any) {
            setError(e.message || 'fetch failed');
        } finally {
            setLoading(false);
        }
    };

    const fetchDiscoveries = async () => {
        try {
            const r = await fetch('/api/v1/property-finder/discoveries');
            if (!r.ok) return;
            setDiscoveries(await r.json());
        } catch { /* ignore */ }
    };

    const triggerCronRefresh = async () => {
        setRefreshing(true);
        try {
            await fetch('/api/v1/property-finder/cron/refresh');
            await Promise.all([fetchShortlist(), fetchDiscoveries()]);
        } finally {
            setRefreshing(false);
        }
    };

    const fetchUrls = async () => {
        try {
            const r = await fetch('/api/v1/property-finder/urls');
            const j = await r.json();
            setPastedUrls(j.urls || []);
        } catch { /* ignore */ }
    };

    const submitUrls = async () => {
        const lines = newUrls.split('\n').map(l => l.trim()).filter(Boolean);
        if (!lines.length) return;
        await fetch('/api/v1/property-finder/urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls: lines }),
        });
        setNewUrls('');
        await fetchUrls();
        await fetchShortlist();
    };

    const removeUrl = async (url: string) => {
        await fetch('/api/v1/property-finder/urls', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
        await fetchUrls();
        await fetchShortlist();
    };

    useEffect(() => {
        fetchShortlist();
        fetchUrls();
        fetchDiscoveries();
    }, []);

    const lastRunRelative = (() => {
        if (!discoveries?.last_run_at) return 'never';
        const ms = Date.now() - new Date(discoveries.last_run_at).getTime();
        const min = Math.floor(ms / 60000);
        if (min < 1) return 'just now';
        if (min < 60) return `${min}m ago`;
        const hr = Math.floor(min / 60);
        if (hr < 24) return `${hr}h ago`;
        return `${Math.floor(hr / 24)}d ago`;
    })();

    return (
        <section style={{ marginTop: 32 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 16 }}>
                <div>
                    <h2 style={{ fontSize: 18, fontWeight: 600, letterSpacing: '-0.01em' }}>Property Finder</h2>
                    <p style={{ fontSize: 13, color: 'var(--fg-2)', marginTop: 4 }}>
                        IFSC · Killester · D03 · D07 · ≤€2,700/mo · furnished · move-in 1 Jun 2026
                        <span style={{ marginLeft: 8, color: 'var(--fg-2)' }}>· cron last ran {lastRunRelative}</span>
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                    <button
                        onClick={triggerCronRefresh}
                        disabled={refreshing}
                        style={{
                            padding: '6px 12px', fontSize: 12, borderRadius: 6,
                            background: 'var(--bg-1)', color: 'var(--fg-1)', border: '1px solid var(--border-1)',
                            cursor: refreshing ? 'not-allowed' : 'pointer',
                        }}
                        title="Run the cron refresh now (same path Vercel hits every 30 min)"
                    >
                        {refreshing ? 'Discovering…' : 'Run cron now'}
                    </button>
                    <button
                        onClick={fetchShortlist}
                        style={{
                            padding: '6px 12px', fontSize: 12, borderRadius: 6,
                            background: 'var(--bg-1)', color: 'var(--fg-1)', border: '1px solid var(--border-1)',
                            cursor: 'pointer',
                        }}
                    >
                        {loading ? 'Refreshing…' : 'Refresh'}
                    </button>
                </div>
            </div>

            {error && (
                <div style={{ padding: 12, background: '#7f1d1d', color: '#fecaca', borderRadius: 8, marginBottom: 16 }}>
                    Error: {error}
                </div>
            )}

            {/* Sources status */}
            {data?.sources && (
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
                    {data.sources.map(s => (
                        <span
                            key={s.name}
                            style={{
                                padding: '4px 10px', fontSize: 11, borderRadius: 999,
                                background: s.ok ? 'rgba(34, 197, 94, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                                color: s.ok ? '#22c55e' : '#ef4444',
                                border: `1px solid ${s.ok ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                            }}
                            title={s.note}
                        >
                            {sourceLabel(s.name)}: {s.count} {s.ok ? '✓' : '✗'}
                        </span>
                    ))}
                </div>
            )}

            {/* Recommended pick */}
            {data?.recommended_pick && (
                <div
                    style={{
                        padding: 16, marginBottom: 16,
                        background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.08), rgba(59, 130, 246, 0.08))',
                        border: '1px solid rgba(34, 197, 94, 0.25)',
                        borderRadius: 10,
                        display: 'flex', gap: 14, alignItems: 'stretch',
                    }}
                >
                    {data.recommended_pick.listing.image_url && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                            src={data.recommended_pick.listing.image_url}
                            alt={data.recommended_pick.listing.address_rough}
                            style={{
                                width: 200, height: 140, objectFit: 'cover',
                                borderRadius: 8, flexShrink: 0,
                            }}
                        />
                    )}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flex: 1 }}>
                        <div>
                            <div style={{ fontSize: 11, color: '#22c55e', fontWeight: 600, marginBottom: 4 }}>
                                ★ RECOMMENDED PICK
                            </div>
                            <div style={{ fontSize: 16, fontWeight: 600 }}>
                                {data.recommended_pick.listing.address_rough}
                            </div>
                            <div style={{ fontSize: 13, color: 'var(--fg-2)', marginTop: 4 }}>
                                {data.recommended_pick.why_this}
                            </div>
                        </div>
                        <a
                            href={data.recommended_pick.listing.source_url}
                            target="_blank" rel="noreferrer"
                            style={{
                                padding: '8px 14px', fontSize: 12, borderRadius: 6,
                                background: '#22c55e', color: '#052e16', textDecoration: 'none', fontWeight: 600,
                                whiteSpace: 'nowrap',
                            }}
                        >
                            View listing →
                        </a>
                    </div>
                </div>
            )}

            {/* Listings grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
                {data?.ranked_listings.map(r => {
                    const isNew = discoveries?.recent_new_ids?.includes(r.listing.canonical_id);
                    return (
                    <div
                        key={r.listing.canonical_id}
                        style={{
                            background: 'var(--bg-1)',
                            border: isNew ? '1px solid rgba(34, 197, 94, 0.5)' : '1px solid var(--border-1)',
                            borderRadius: 10,
                            display: 'flex', flexDirection: 'column',
                            position: 'relative',
                            overflow: 'hidden',
                        }}
                    >
                        {r.listing.image_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                                src={r.listing.image_url}
                                alt={r.listing.address_rough}
                                style={{
                                    width: '100%', height: 180, objectFit: 'cover',
                                    background: 'var(--bg-2, #1a1a1a)',
                                }}
                                loading="lazy"
                            />
                        ) : (
                            <div style={{
                                width: '100%', height: 180, background: 'var(--bg-2, #1a1a1a)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                color: 'var(--fg-2)', fontSize: 11,
                            }}>
                                no image
                            </div>
                        )}
                        <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
                        {isNew && (
                            <span
                                style={{
                                    position: 'absolute', top: 8, right: 8,
                                    padding: '2px 8px', fontSize: 10, fontWeight: 600,
                                    background: '#22c55e', color: '#052e16', borderRadius: 999,
                                }}
                            >
                                NEW
                            </span>
                        )}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div>
                                <div style={{ fontSize: 11, color: 'var(--fg-2)' }}>
                                    #{r.rank} · {sourceLabel(r.listing.source)} · {r.listing.area_routing_key}
                                </div>
                                <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>
                                    {r.listing.address_rough}
                                </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ fontSize: 16, fontWeight: 700 }}>€{r.listing.rent_eur.toLocaleString()}</div>
                                <div style={{ fontSize: 10, color: 'var(--fg-2)' }}>
                                    {r.listing.bills_included ? 'bills inc.' : `+~€${r.listing.estimated_bills_eur} bills`}
                                </div>
                            </div>
                        </div>

                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', fontSize: 11, color: 'var(--fg-2)' }}>
                            <span>🛏 {r.listing.beds === 0 ? 'studio' : `${r.listing.beds} bed`}</span>
                            <span>🛁 {r.listing.baths}</span>
                            {r.listing.ber_rating && <span>⚡ BER {r.listing.ber_rating}</span>}
                            {r.listing.floor_area_sqm && <span>📐 {r.listing.floor_area_sqm}m²</span>}
                            {r.listing.parking_available && <span>🅿 parking</span>}
                            {r.listing.lease_length_months && <span>📅 {r.listing.lease_length_months}mo lease</span>}
                        </div>

                        <div style={{ fontSize: 12, color: 'var(--fg-1)' }}>
                            {r.why_this}
                        </div>

                        <div style={{ display: 'flex', gap: 6, fontSize: 10, color: 'var(--fg-2)' }}>
                            <span>commute ~{r.scores.commute_minutes}min</span>
                            <span>· quality {Math.round(r.scores.listing_quality_score * 100)}%</span>
                            {r.scores.rpz_flag && <span>· RPZ</span>}
                            {r.scores.affordability_verdict && (
                                <span style={{ color: verdictColor(r.scores.affordability_verdict) }}>
                                    · {r.scores.affordability_verdict}
                                </span>
                            )}
                        </div>

                        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                            <a
                                href={r.listing.source_url}
                                target="_blank" rel="noreferrer"
                                style={{
                                    padding: '5px 10px', fontSize: 11, borderRadius: 5,
                                    background: 'var(--bg-2, #2a2a2a)', color: 'var(--fg-1)',
                                    textDecoration: 'none', flex: 1, textAlign: 'center',
                                    border: '1px solid var(--border-1)',
                                }}
                            >
                                View on {sourceLabel(r.listing.source)} →
                            </a>
                        </div>
                        </div>
                    </div>
                    );
                })}
            </div>

            {/* Readiness snapshot — hidden while user is in rent-only mode */}
            {false && data?.readiness_snapshot && (
                <div
                    style={{
                        marginTop: 16, padding: 14,
                        background: 'var(--bg-1)', border: '1px solid var(--border-1)', borderRadius: 10,
                    }}
                >
                    <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Buying-readiness snapshot</div>
                    <div style={{ fontSize: 12, color: 'var(--fg-2)', lineHeight: 1.6 }}>
                        <div><strong>Next action:</strong> {data?.readiness_snapshot?.next_concrete_action}</div>
                        <div><strong>AIP:</strong> {data?.readiness_snapshot?.aip_action}</div>
                        <div><strong>Schemes:</strong> {data?.readiness_snapshot?.scheme_recommendation}</div>
                        <div style={{ marginTop: 8, fontStyle: 'italic', fontSize: 11 }}>
                            {data?.readiness_snapshot?.not_regulated_advice_note}
                        </div>
                    </div>
                </div>
            )}

            {/* URL paste box */}
            <div
                style={{
                    marginTop: 16, padding: 14,
                    background: 'var(--bg-1)', border: '1px dashed var(--border-1)', borderRadius: 10,
                }}
            >
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                    Paste listing URLs (Daft / MyHome / Sherry FitzGerald / DNG / Hooke & MacDonald / Lisney)
                </div>
                <div style={{ fontSize: 11, color: 'var(--fg-2)', marginBottom: 8 }}>
                    Open a search below, copy listing URLs, paste here. Real photos are pulled from each page's og:image tag.
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                    {[
                        { label: 'Daft · IFSC ≤€2.7k', href: 'https://www.daft.ie/property-for-rent/ifsc-dublin?rentalPrice_to=2700&furnishing=furnished' },
                        { label: 'Daft · Killester ≤€2.7k', href: 'https://www.daft.ie/property-for-rent/killester-dublin?rentalPrice_to=2700&furnishing=furnished' },
                        { label: 'Daft · Houses D3/D5', href: 'https://www.daft.ie/property-for-rent/houses/dublin?rentalPrice_to=2700&propertyType=houses&furnishing=furnished' },
                        { label: 'MyHome · D1 ≤€2.7k', href: 'https://www.myhome.ie/rentals/dublin-1/property?maxprice=2700' },
                        { label: 'MyHome · D5 ≤€2.7k', href: 'https://www.myhome.ie/rentals/dublin-5/property?maxprice=2700' },
                        { label: 'MyHome · Brookwood', href: 'https://www.myhome.ie/rentals/property?location=brookwood-killester-dublin-5&maxprice=2700' },
                        { label: 'Sherry FitzGerald · Lettings', href: 'https://www.sherryfitz.ie/lettings' },
                        { label: 'Hooke & MacDonald', href: 'https://www.hookemacdonald.ie/letting/' },
                        { label: 'DNG · Lettings', href: 'https://www.dng.ie/lettings/' },
                        { label: 'Lisney · Lettings', href: 'https://www.lisney.com/lettings/' },
                    ].map(link => (
                        <a
                            key={link.href}
                            href={link.href}
                            target="_blank" rel="noreferrer"
                            style={{
                                padding: '5px 10px', fontSize: 11, borderRadius: 5,
                                background: 'var(--bg-0)', color: 'var(--fg-1)', textDecoration: 'none',
                                border: '1px solid var(--border-1)',
                            }}
                        >
                            {link.label} ↗
                        </a>
                    ))}
                </div>
                <textarea
                    value={newUrls}
                    onChange={e => setNewUrls(e.target.value)}
                    placeholder="https://www.myhome.ie/…&#10;https://www.sherryfitz.ie/…"
                    rows={3}
                    style={{
                        width: '100%', padding: 8, fontSize: 12, fontFamily: 'monospace',
                        background: 'var(--bg-0)', color: 'var(--fg-1)',
                        border: '1px solid var(--border-1)', borderRadius: 6, resize: 'vertical',
                    }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                    <span style={{ fontSize: 11, color: 'var(--fg-2)' }}>
                        {pastedUrls.length} URL{pastedUrls.length !== 1 ? 's' : ''} stored
                    </span>
                    <button
                        onClick={submitUrls}
                        disabled={!newUrls.trim()}
                        style={{
                            padding: '6px 14px', fontSize: 12, borderRadius: 6,
                            background: newUrls.trim() ? 'var(--accent, #3b82f6)' : 'var(--bg-2, #2a2a2a)',
                            color: '#fff', border: 'none',
                            cursor: newUrls.trim() ? 'pointer' : 'not-allowed',
                        }}
                    >
                        Add URLs & re-rank
                    </button>
                </div>
                {pastedUrls.length > 0 && (
                    <ul style={{ marginTop: 10, padding: 0, listStyle: 'none', fontSize: 11 }}>
                        {pastedUrls.map(u => (
                            <li key={u} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid var(--border-1)' }}>
                                <a href={u} target="_blank" rel="noreferrer" style={{ color: 'var(--fg-2)', textDecoration: 'none', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '85%' }}>
                                    {u}
                                </a>
                                <button
                                    onClick={() => removeUrl(u)}
                                    style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 11 }}
                                >
                                    ×
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            {data?.spec_notes && (
                <div style={{ marginTop: 12, fontSize: 11, color: 'var(--fg-2)', fontStyle: 'italic' }}>
                    {data.spec_notes}
                </div>
            )}
        </section>
    );
}
