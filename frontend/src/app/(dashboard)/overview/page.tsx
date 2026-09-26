'use client';

import { useState, useEffect } from 'react';
import { fetchApi } from '@/lib/api';
import { Activity, AlertTriangle, Zap, Server, ClipboardList, TrendingUp } from 'lucide-react';
import Link from 'next/link';

export default function OverviewPage() {
  const [stats, setStats] = useState({
    events: 0,
    workOrders: 0,
    machines: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadOverview = async () => {
      try {
        // Fetch real data where possible
        const [eventsData, woData, machinesData] = await Promise.all([
          fetchApi('/events/?limit=1').catch(() => []),
          fetchApi('/work-orders?limit=1').catch(() => ({ total: 0 })),
          fetchApi('/machines?limit=1').catch(() => ({ total: 0 })),
        ]);
        
        setStats({
          events: Array.isArray(eventsData) ? eventsData.length : 0, // Just a placeholder indicator
          workOrders: woData.total || 0,
          machines: machinesData.total || 0,
        });
      } catch (e) {
        console.error('Failed to load overview data', e);
      } finally {
        setLoading(false);
      }
    };
    
    loadOverview();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Production Overview</h1>
        <p className="text-sm text-slate-400 mt-1">Real-time intelligence and operational status across your facility.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Stat Card 1 */}
        <div className="bg-[#080f23]/50 backdrop-blur-md border border-white/10 rounded-2xl p-6 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Zap className="w-16 h-16 text-[var(--color-x-cyan)]" />
          </div>
          <div className="relative z-10">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Total Events</p>
            <div className="flex items-baseline gap-2">
              <h2 className="text-3xl font-bold text-white">{loading ? '...' : (stats.events > 0 ? `${stats.events}+` : '0')}</h2>
              <span className="text-xs font-medium text-[var(--color-x-cyan)] flex items-center">
                <TrendingUp className="w-3 h-3 mr-1" /> Live
              </span>
            </div>
          </div>
        </div>

        {/* Stat Card 2 */}
        <div className="bg-[#080f23]/50 backdrop-blur-md border border-white/10 rounded-2xl p-6 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <AlertTriangle className="w-16 h-16 text-[var(--color-x-amber)]" />
          </div>
          <div className="relative z-10">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Active Risks</p>
            <div className="flex items-baseline gap-2">
              <h2 className="text-xl font-bold text-slate-500">N/A</h2>
              <span className="text-xs font-medium text-slate-600">Awaiting ML Engine</span>
            </div>
          </div>
        </div>

        {/* Stat Card 3 */}
        <div className="bg-[#080f23]/50 backdrop-blur-md border border-white/10 rounded-2xl p-6 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <ClipboardList className="w-16 h-16 text-white" />
          </div>
          <div className="relative z-10">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Work Orders</p>
            <div className="flex items-baseline gap-2">
              <h2 className="text-3xl font-bold text-white">{loading ? '...' : stats.workOrders}</h2>
              <span className="text-xs font-medium text-slate-500">Tracked</span>
            </div>
          </div>
        </div>

        {/* Stat Card 4 */}
        <div className="bg-[#080f23]/50 backdrop-blur-md border border-white/10 rounded-2xl p-6 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Server className="w-16 h-16 text-[var(--color-x-teal)]" />
          </div>
          <div className="relative z-10">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Machines</p>
            <div className="flex items-baseline gap-2">
              <h2 className="text-3xl font-bold text-white">{loading ? '...' : stats.machines}</h2>
              <span className="text-xs font-medium text-[var(--color-x-green)] flex items-center">
                <span className="w-2 h-2 rounded-full bg-[var(--color-x-green)] mr-1.5 animate-pulse"></span> Online
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Signal Feed Preview */}
        <div className="lg:col-span-2 bg-[#080f23]/50 backdrop-blur-md border border-white/10 rounded-2xl flex flex-col h-[400px]">
          <div className="p-5 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-[var(--color-x-cyan)]" />
              <h3 className="font-semibold text-white">Live Signal Feed</h3>
            </div>
            <Link href="/events" className="text-xs text-[var(--color-x-cyan)] hover:text-cyan-300 font-medium transition-colors">
              View All
            </Link>
          </div>
          <div className="flex-1 p-5 flex items-center justify-center text-slate-500">
            {loading ? (
              <div className="flex flex-col items-center gap-3">
                <div className="w-8 h-8 rounded-full border-2 border-[var(--color-x-cyan)] border-t-transparent animate-spin"></div>
                <span className="text-sm">Connecting to stream...</span>
              </div>
            ) : (
              <div className="text-center">
                <Activity className="w-12 h-12 text-slate-600 mx-auto mb-3 opacity-50" />
                <p className="text-sm">Signal feed is empty or awaiting integration.</p>
                <Link href="/imports" className="mt-4 inline-block px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs text-white transition-all">
                  Import Data
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Risk / Alerts */}
        <div className="bg-[#080f23]/50 backdrop-blur-md border border-white/10 rounded-2xl flex flex-col h-[400px]">
          <div className="p-5 border-b border-white/10">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-[var(--color-x-amber)]" />
              <h3 className="font-semibold text-white">Production Risk</h3>
            </div>
          </div>
          <div className="flex-1 p-5 flex items-center justify-center text-slate-500">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-slate-800/50 border border-slate-700 flex items-center justify-center mx-auto mb-3">
                <div className="w-3 h-3 rounded-full bg-slate-500"></div>
              </div>
              <p className="text-sm font-medium text-slate-400">Risk Data Unavailable</p>
              <p className="text-xs text-slate-600 mt-1">Production risk engine is not yet connected.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
