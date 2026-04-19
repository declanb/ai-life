'use client';

import React, { useEffect, useState } from 'react';

interface Departure {
    route: string;
    destination: string;
    due_minutes: string;
    scheduled: string;
    realtime: string;
    mode: 'bus' | 'luas';
}

interface StopDepartures {
    stop_id: string;
    stop_name: string;
    departures: Departure[];
    error?: string;
}

interface CommuteOption {
    stop_name: string;
    stop_id: string;
    route: string;
    destination: string;
    due_minutes: number;
    due_str: string;
    leave_at: string;
    leave_in_minutes: number;
    walk_minutes: number;
    mode: 'bus' | 'luas';
}

interface CommuteData {
    direction: string;
    origin: string;
    destination: string;
    options: CommuteOption[];
    recommendation: string | null;
    walk_minutes: number;
}

interface SavedStop {
    id: string;
    name: string;
    type: 'bus' | 'luas';
}

export default function TransitDashboard() {
    const [commuteToWork, setCommuteToWork] = useState<CommuteData | null>(null);
    const [commuteToHome, setCommuteToHome] = useState<CommuteData | null>(null);
    const [stops, setStops] = useState<SavedStop[]>([
        { id: "334", name: "Phibsborough", type: "bus" },
        { id: "JER", name: "Jervis", type: "luas" }
    ]);
    const [departures, setDepartures] = useState<Record<string, StopDepartures>>({});
    const [loading, setLoading] = useState(true);
    const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
    const [secondsSinceUpdate, setSecondsSinceUpdate] = useState(0);

    const fetchCommuteData = async () => {
        try {
            const [toWorkRes, toHomeRes] = await Promise.all([
                fetch('/api/v1/transit/commute/to-work'),
                fetch('/api/v1/transit/commute/to-home')
            ]);
            
            if (toWorkRes.ok) {
                setCommuteToWork(await toWorkRes.json());
            }
            if (toHomeRes.ok) {
                setCommuteToHome(await toHomeRes.json());
            }
        } catch (err: any) {
            console.error("Error fetching commute data:", err);
        }
    };

    const fetchDepartures = async () => {
        try {
            const results: Record<string, StopDepartures> = {};
            
            for (const stop of stops) {
                const endpoint = stop.type === 'luas' 
                    ? `/api/v1/transit/luas/stop/${stop.id}`
                    : `/api/v1/transit/bus/stop/${stop.id}`;
                
                const res = await fetch(endpoint);
                if (res.ok) {
                    results[stop.id] = await res.json();
                }
            }
            
            setDepartures(results);
        } catch (err: any) {
            console.error("Error fetching transit data:", err);
        }
    };

    const refreshAll = async () => {
        setLoading(true);
        await Promise.all([fetchCommuteData(), fetchDepartures()]);
        setLastUpdate(new Date());
        setSecondsSinceUpdate(0);
        setLoading(false);
    };

    useEffect(() => {
        refreshAll();
        const interval = setInterval(refreshAll, 30000);
        return () => clearInterval(interval);
    }, [stops]);

    useEffect(() => {
        const timer = setInterval(() => {
            setSecondsSinceUpdate(Math.floor((new Date().getTime() - lastUpdate.getTime()) / 1000));
        }, 1000);
        return () => clearInterval(timer);
    }, [lastUpdate]);

    if (loading && !commuteToWork && !commuteToHome) {
        return (
            <div className="p-8 text-center text-gray-400">
                Loading Dublin Transit Data...
            </div>
        );
    }

    const renderCommuteCard = (data: CommuteData | null, title: string, emoji: string) => {
        if (!data) return null;

        return (
            <section className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-3xl border border-blue-500/20 backdrop-blur-xl overflow-hidden">
                <div className="p-6 border-b border-white/10 bg-white/5">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-2xl font-bold text-white flex items-center gap-3">
                                <span>{emoji}</span>
                                {title}
                            </h3>
                            <p className="text-xs text-gray-400 mt-1">
                                {data.origin} → {data.destination}
                            </p>
                        </div>
                        {data.recommendation && (
                            <div className="text-right">
                                <div className="text-sm font-black text-yellow-400">
                                    {data.recommendation.split(' for ')[0]}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <div className="divide-y divide-white/5">
                    {data.options && data.options.length > 0 ? (
                        data.options.map((opt, i) => (
                            <div key={i} className="p-4 hover:bg-white/[0.05] transition-all">
                                <div className="flex items-center justify-between gap-4">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-3 mb-1">
                                            <span className={`px-2 py-1 rounded-lg text-xs font-black ${
                                                opt.mode === 'luas' 
                                                    ? 'bg-green-500/20 text-green-300' 
                                                    : 'bg-blue-500/20 text-blue-300'
                                            }`}>
                                                {opt.route}
                                            </span>
                                            <span className="text-sm text-gray-400 truncate">
                                                from {opt.stop_name}
                                            </span>
                                        </div>
                                        <div className="text-xs text-gray-500 truncate">
                                            → {opt.destination}
                                        </div>
                                    </div>
                                    <div className="text-right flex-shrink-0">
                                        <div className={`text-3xl font-black ${
                                            opt.due_str === 'Due' || opt.due_minutes <= 5
                                                ? 'text-yellow-400'
                                                : 'text-green-400'
                                        }`}>
                                            {opt.due_str === 'Due' ? 'DUE' : opt.due_minutes}
                                        </div>
                                        <div className="text-xs text-gray-500 font-medium">
                                            {opt.due_str !== 'Due' && 'min'}
                                        </div>
                                        <div className="mt-2 text-base font-bold text-white">
                                            Leave at {opt.leave_at}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            ({opt.walk_minutes} min walk)
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="p-8 text-center text-gray-500">
                            No upcoming departures
                        </div>
                    )}
                </div>
            </section>
        );
    };

    return (
        <div className="p-6 max-w-6xl mx-auto mt-8">
            <div className="flex justify-between items-center mb-12 bg-white/5 p-8 rounded-3xl border border-white/10 backdrop-blur-2xl">
                <div>
                    <h2 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-green-400 via-blue-400 to-purple-400">
                        Dublin Transit
                    </h2>
                    <p className="text-gray-400 mt-2">
                        Live bus & Luas departures · Updated {secondsSinceUpdate}s ago
                    </p>
                </div>
                <button
                    onClick={refreshAll}
                    className="px-6 py-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-bold hover:bg-blue-500/20 transition-all"
                >
                    Refresh Now
                </button>
            </div>

            <div className="space-y-6 mb-12">
                <h3 className="text-2xl font-bold text-white px-2">Your Commute</h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {renderCommuteCard(commuteToWork, "Get to Harcourt", "🏢")}
                    {renderCommuteCard(commuteToHome, "Get home to Coolock", "🏠")}
                </div>
            </div>

            <h3 className="text-2xl font-bold text-white px-2 mb-6">Other Stops</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
                {stops.map((stop) => {
                    const data = departures[stop.id];
                    if (!data) return null;

                    return (
                        <section key={stop.id} className="bg-white/5 rounded-3xl border border-white/10 backdrop-blur-xl overflow-hidden">
                            <div className="p-6 border-b border-white/10 bg-white/5">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="text-xl font-bold text-white">
                                            {data.stop_name}
                                        </h3>
                                        <p className="text-xs text-gray-400 mt-1">
                                            {stop.type === 'luas' ? '🚊 Luas' : '🚌 Dublin Bus'} · Stop {stop.id}
                                        </p>
                                    </div>
                                    <span className="flex h-3 w-3 relative">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                                    </span>
                                </div>
                            </div>

                            <div className="divide-y divide-white/5">
                                {data.departures && data.departures.length > 0 ? (
                                    data.departures.slice(0, 5).map((dep, i) => (
                                        <div key={i} className="p-4 hover:bg-white/[0.05] transition-all">
                                            <div className="flex items-center justify-between">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-3">
                                                        <span className="px-2 py-1 rounded-lg bg-blue-500/20 text-blue-300 text-xs font-black">
                                                            {dep.route}
                                                        </span>
                                                        <span className="text-sm text-white font-medium">
                                                            {dep.destination}
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    <div className={`text-2xl font-black ${
                                                        dep.due_minutes === 'Due' || (dep.due_minutes.match(/^\d+$/) && parseInt(dep.due_minutes) <= 5)
                                                            ? 'text-yellow-400'
                                                            : 'text-green-400'
                                                    }`}>
                                                        {dep.due_minutes === 'Due' ? 'DUE' : `${dep.due_minutes}`}
                                                    </div>
                                                    {dep.due_minutes !== 'Due' && dep.due_minutes.match(/^\d+$/) && (
                                                        <div className="text-xs text-gray-500 font-medium">
                                                            min
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="p-8 text-center text-gray-500">
                                        {data.error ? `Error: ${data.error}` : 'No departures'}
                                    </div>
                                )}
                            </div>
                        </section>
                    );
                })}
            </div>

            <section className="mt-12 bg-white/5 rounded-3xl border border-white/10 backdrop-blur-xl p-8">
                <h3 className="text-2xl font-bold text-white mb-6">Plan Your Commute</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-semibold text-gray-400 mb-2">Stop ID or Name</label>
                            <input 
                                type="text" 
                                placeholder="e.g. 334, JER, Phibsborough"
                                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50 transition-all"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-semibold text-gray-400 mb-2">Route (optional)</label>
                            <input 
                                type="text" 
                                placeholder="e.g. 39A, Red Line"
                                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50 transition-all"
                            />
                        </div>
                    </div>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-semibold text-gray-400 mb-2">Walk Time (minutes)</label>
                            <input 
                                type="number" 
                                defaultValue={5}
                                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50 transition-all"
                            />
                        </div>
                        <button className="w-full px-6 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 text-white font-bold hover:from-blue-600 hover:to-purple-600 transition-all shadow-lg shadow-blue-500/20">
                            Get Commute Alert
                        </button>
                    </div>
                </div>
                <p className="text-xs text-gray-500 mt-4 text-center">
                    Commute alerts will notify you when to leave based on live departures + your walk time
                </p>
            </section>
        </div>
    );
}
}
