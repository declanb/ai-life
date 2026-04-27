'use client';

import React, { useEffect, useState } from 'react';

interface SyncStatus {
    last_export_run_id: string | null;
    total_photos_discovered: number;
    total_photos_exported: number;
    total_photos_uploaded: number;
    pending_uploads: number;
    failed_photos: number;
    last_sync_at: string | null;
}

export default function PhotosDashboard() {
    const [status, setStatus] = useState<SyncStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [syncing, setSyncing] = useState(false);

    const fetchStatus = async () => {
        try {
            const res = await fetch('/api/v1/photos/sync/status');
            if (!res.ok) throw new Error('Failed to fetch sync status');
            const data = await res.json();
            setStatus(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
    }, []);

    const handleSyncDryRun = async () => {
        if (!confirm("Run a DRY-RUN sync? This will export from iCloud but NOT upload to Google Photos.")) return;

        setSyncing(true);
        try {
            const res = await fetch('/api/v1/photos/sync/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dry_run: true }),
            });
            const data = await res.json();
            alert(data.message);
            await fetchStatus();
        } catch (err: any) {
            alert("Error running dry-run sync: " + err.message);
        } finally {
            setSyncing(false);
        }
    };

    const handleSyncLive = async () => {
        if (!confirm(
            "CRITICAL ACTION: Run a LIVE sync? This will UPLOAD photos to Google Photos.\n\n" +
            "This is a ONE-WAY mirror. Uploads are permanent and cannot be deleted via API.\n\n" +
            "Are you sure?"
        )) return;

        setSyncing(true);
        try {
            const res = await fetch('/api/v1/photos/sync/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dry_run: false }),
            });
            const data = await res.json();
            alert(data.message);
            await fetchStatus();
        } catch (err: any) {
            alert("Error running live sync: " + err.message);
        } finally {
            setSyncing(false);
        }
    };

    if (loading) return <div className="p-8 text-center text-gray-400">Loading Photos Mirror Status...</div>;
    if (error) return <div className="p-8 text-center text-red-400">Error: {error}</div>;

    return (
        <div className="p-6 max-w-6xl mx-auto">
            <div className="flex justify-between items-center mb-12 bg-white/5 p-8 rounded-3xl border border-white/10 backdrop-blur-2xl">
                <div>
                    <h2 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400">
                        Photos Mirror
                    </h2>
                    <p className="text-gray-400 mt-2">iCloud → Google Photos one-way mirror</p>
                </div>
                <div className="flex gap-4">
                    <button
                        onClick={handleSyncDryRun}
                        disabled={syncing}
                        className="px-6 py-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-bold hover:bg-blue-500/20 transition-all disabled:opacity-50"
                    >
                        {syncing ? "Syncing..." : "Run Sync (Dry-Run)"}
                    </button>
                    <button
                        onClick={handleSyncLive}
                        disabled={syncing}
                        className="px-6 py-3 rounded-2xl bg-red-500/20 border border-red-500/30 text-red-400 text-sm font-bold hover:bg-red-500/30 transition-all disabled:opacity-50 shadow-2xl shadow-red-500/20"
                    >
                        {syncing ? "Uploading..." : "Run Sync (LIVE)"}
                    </button>
                </div>
            </div>

            <section className="mb-16">
                <h3 className="text-2xl font-semibold mb-8 text-white flex items-center gap-3">
                    <span className="flex h-3 w-3 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                    Sync Status
                </h3>
                <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8">
                    <div className="grid grid-cols-3 gap-6">
                        <div>
                            <p className="text-sm text-gray-400 mb-2">Photos Discovered</p>
                            <p className="text-3xl font-bold text-white">{status?.total_photos_discovered || 0}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-400 mb-2">Photos Exported</p>
                            <p className="text-3xl font-bold text-white">{status?.total_photos_exported || 0}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-400 mb-2">Photos Uploaded</p>
                            <p className="text-3xl font-bold text-white">{status?.total_photos_uploaded || 0}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-400 mb-2">Pending Uploads</p>
                            <p className="text-3xl font-bold text-yellow-400">{status?.pending_uploads || 0}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-400 mb-2">Failed Photos</p>
                            <p className="text-3xl font-bold text-red-400">{status?.failed_photos || 0}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-400 mb-2">Last Sync</p>
                            <p className="text-lg font-bold text-white">
                                {status?.last_sync_at ? new Date(status.last_sync_at).toLocaleString() : 'Never'}
                            </p>
                        </div>
                    </div>
                    {status?.last_export_run_id && (
                        <div className="mt-6 pt-6 border-t border-white/10">
                            <p className="text-sm text-gray-400">Last Export Run ID</p>
                            <p className="text-sm text-gray-300 font-mono mt-1">{status.last_export_run_id}</p>
                        </div>
                    )}
                </div>
            </section>

            <section>
                <h3 className="text-2xl font-semibold mb-8 text-white">Architecture Notes</h3>
                <div className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8">
                    <ul className="space-y-3 text-gray-300">
                        <li className="flex items-start gap-3">
                            <span className="text-green-400">✓</span>
                            <span><strong>Source of Truth:</strong> iCloud Photos (synced to Mac via Photos.app)</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="text-green-400">✓</span>
                            <span><strong>Export Agent:</strong> osxphotos CLI on Mac (preserves Live Photos, EXIF, edits)</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="text-green-400">✓</span>
                            <span><strong>Mirror Destination:</strong> Google Photos (append-only, no deletes via API)</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="text-yellow-400">⚠</span>
                            <span><strong>Dedupe:</strong> SHA-256 + perceptual hash (stored in local SQLite)</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="text-red-400">✗</span>
                            <span><strong>No Deletes:</strong> Google Photos Library API does not support deletion. Manual only.</span>
                        </li>
                    </ul>
                </div>
            </section>
        </div>
    );
}
