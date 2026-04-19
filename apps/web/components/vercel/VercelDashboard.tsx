'use client';

import React, { useEffect, useState } from 'react';

interface Project {
    name: string;
    url: string;
    updated: string;
}

interface Deployment {
    project: string;
    url: string;
    status: string;
    type: string;
    age: string;
}

export default function VercelDashboard() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [deployments, setDeployments] = useState<Deployment[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [stopping, setStopping] = useState(false);

    const fetchData = async () => {
        try {
            const [projRes, depRes] = await Promise.all([
                fetch('/api/v1/vercel/projects'),
                fetch('/api/v1/vercel/deployments')
            ]);

            if (!projRes.ok || !depRes.ok) throw new Error('Failed to fetch Vercel data');

            const [projData, depData] = await Promise.all([projRes.json(), depRes.json()]);
            setProjects(projData);
            setDeployments(depData);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleStopAll = async () => {
        if (!confirm("Are you sure you want to stop all in-progress (building) deployments?")) return;

        setStopping(true);
        try {
            const res = await fetch('/api/v1/vercel/stop', { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            await fetchData();
        } catch (err: any) {
            alert("Error stopping deployments: " + err.message);
        } finally {
            setStopping(false);
        }
    };

    const handleStopProduction = async () => {
        if (!confirm("CRITICAL ACTION: Are you sure you want to STOP (REMOVE) ALL PRODUCTION DEPLOYMENTS? This will take your sites offline.")) return;

        setStopping(true);
        try {
            const res = await fetch('/api/v1/vercel/stop-production', { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            await fetchData();
        } catch (err: any) {
            alert("Error stopping production deployments: " + err.message);
        } finally {
            setStopping(false);
        }
    };

    if (loading) return <div className="p-8 text-center text-gray-400">Loading Vercel Data...</div>;
    if (error) return <div className="p-8 text-center text-red-400">Error: {error}</div>;

    return (
        <div className="p-6 max-w-6xl mx-auto">
            <div className="flex justify-between items-center mb-12 bg-white/5 p-8 rounded-3xl border border-white/10 backdrop-blur-2xl">
                <div>
                    <h2 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400">
                        Vercel Assistant
                    </h2>
                    <p className="text-gray-400 mt-2">Manage your cloud infrastructure automation.</p>
                </div>
                <div className="flex gap-4">
                    <button
                        onClick={handleStopAll}
                        disabled={stopping}
                        className="px-6 py-3 rounded-2xl bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-sm font-bold hover:bg-yellow-500/20 transition-all disabled:opacity-50"
                    >
                        {stopping ? "Processing..." : "Stop In-Progress"}
                    </button>
                    <button
                        onClick={handleStopProduction}
                        disabled={stopping}
                        className="px-6 py-3 rounded-2xl bg-red-500/20 border border-red-500/30 text-red-400 text-sm font-bold hover:bg-red-500/30 transition-all disabled:opacity-50 shadow-2xl shadow-red-500/20"
                    >
                        {stopping ? "Removing Production..." : "Stop All Production"}
                    </button>
                </div>
            </div>

            <section className="mb-16">
                <h3 className="text-2xl font-semibold mb-8 text-white flex items-center gap-3">
                    <span className="flex h-3 w-3 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                    Live Deployment Monitor
                </h3>
                <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-white/10 bg-white/5 text-[11px] uppercase tracking-[0.2em] text-gray-500">
                                    <th className="px-8 py-5 font-bold">Project / ID</th>
                                    <th className="px-8 py-5 font-bold">Endpoint</th>
                                    <th className="px-8 py-5 font-bold text-center">Status</th>
                                    <th className="px-8 py-5 font-bold text-center">Type</th>
                                    <th className="px-8 py-5 font-bold text-right">Age</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {deployments.map((dep, i) => (
                                    <tr key={i} className="hover:bg-white/[0.07] transition-all group">
                                        <td className="px-8 py-6 text-sm font-semibold text-white">
                                            {dep.project.split('/').pop()}
                                        </td>
                                        <td className="px-8 py-6 text-sm">
                                            <a href={`https://${dep.url}`} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1">
                                                {dep.url.length > 40 ? dep.url.substring(0, 40) + '...' : dep.url}
                                                <span className="opacity-0 group-hover:opacity-100 transition-opacity">↗</span>
                                            </a>
                                        </td>
                                        <td className="px-8 py-6 text-center">
                                            <span className={`px-3 py-1 rounded-full text-[10px] font-black tracking-widest ${dep.status === 'READY' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                                                }`}>
                                                {dep.status}
                                            </span>
                                        </td>
                                        <td className="px-8 py-6 text-center">
                                            <span className={`px-3 py-1 rounded-full text-[10px] font-black tracking-widest ${dep.type === 'Production' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                                }`}>
                                                {dep.type}
                                            </span>
                                        </td>
                                        <td className="px-8 py-6 text-sm text-gray-500 text-right font-mono">{dep.age}</td>
                                    </tr>
                                ))}
                                {deployments.length === 0 && (
                                    <tr>
                                        <td colSpan={5} className="px-8 py-16 text-center text-gray-500 text-sm italic">
                                            Systems quiet. No active deployments found in scope.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>

            <h3 className="text-2xl font-semibold mb-8 text-white">Infrastructure Overview</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {projects.map((project) => (
                    <div
                        key={project.name}
                        className="group relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-white/10 to-transparent p-8 backdrop-blur-xl transition-all hover:translate-y-[-4px] hover:border-white/20 hover:shadow-2xl hover:shadow-purple-500/10"
                    >
                        <div className="flex justify-between items-start mb-6">
                            <div>
                                <h3 className="text-xl font-bold text-white group-hover:text-blue-400 transition-colors">
                                    {project.name}
                                </h3>
                                <p className="text-sm text-gray-400 mt-1 truncate max-w-[200px]">
                                    {project.url}
                                </p>
                            </div>
                            <div className="p-2 rounded-xl bg-green-500/10 border border-green-500/20">
                                <div className="h-2 w-2 rounded-full bg-green-400"></div>
                            </div>
                        </div>

                        <div className="mt-12 flex justify-between items-end">
                            <div className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">
                                Last Sync: {project.updated}
                            </div>
                            <button
                                className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-xs font-bold text-white hover:bg-white/10 transition-all"
                                onClick={() => window.open(`https://${project.url}`, '_blank')}
                            >
                                Inspect
                            </button>
                        </div>

                        {/* Background Aesthetic */}
                        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-blue-500/5 blur-[80px] group-hover:bg-blue-500/10 transition-all duration-700"></div>
                    </div>
                ))}
            </div>
        </div>
    );
}
