"use client";

import { useState, useEffect } from "react";
import { fetchApi } from "@/lib/api";
import Link from "next/link";

interface ManufacturingEvent {
  id: string;
  company_id: string;
  event_status: string;
  description: string | null;
  canonical_event_type: string | null;
  severity: string | null;
}

export default function ManufacturingEventsPage() {
  const [events, setEvents] = useState<ManufacturingEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination & Filters
  const [page, setPage] = useState(1);
  const limit = 20;
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [eventTypeFilter, setEventTypeFilter] = useState<string>("");

  useEffect(() => {
    const loadEvents = async () => {
      setLoading(true);
      setError(null);
      try {
        const offset = (page - 1) * limit;
        const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
        if (statusFilter) params.append("status", statusFilter);
        if (eventTypeFilter) params.append("event_type", eventTypeFilter);

        const data = await fetchApi(`/events/?${params.toString()}`);
        if (data && data.items) {
          setEvents(data.items);
          setTotal(data.total || 0);
        } else if (Array.isArray(data)) {
          // fallback in case old api
          setEvents(data);
          setTotal(data.length);
        }
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : "Failed to load events";
        setError(message);
      } finally {
        setLoading(false);
      }
    };
    loadEvents();
  }, [page, limit, statusFilter, eventTypeFilter]);

  const getSeverityColor = (severity: string | null) => {
    switch (severity?.toUpperCase()) {
      case "CRITICAL": return "bg-red-500/10 text-red-400";
      case "HIGH": return "bg-orange-100 text-orange-700";
      case "MEDIUM": return "bg-amber-100 text-amber-700";
      case "LOW": return "bg-green-100 text-green-700";
      default: return "bg-white/10 text-slate-400";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "CANONICAL": return "bg-teal-100 text-teal-700";
      case "SUPERSEDED": return "bg-white/10 text-slate-500";
      case "REQUIRES_REVIEW": return "bg-amber-100 text-amber-700";
      case "REJECTED": return "bg-red-100 text-red-700";
      default: return "bg-blue-100 text-cyan-400";
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">Operational Event Inbox</h1>
        <span className="text-sm text-slate-500">
          {!loading && `${total} total event${total !== 1 ? "s" : ""}`}
        </span>
      </div>

      <div className="flex space-x-4 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="bg-[#080f23] text-white border border-slate-700 rounded p-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="CANONICAL">Canonical</option>
          <option value="REQUIRES_REVIEW">Requires Review</option>
          <option value="SUPERSEDED">Superseded</option>
          <option value="REJECTED">Rejected</option>
        </select>

        <input
          type="text"
          placeholder="Filter by event type..."
          value={eventTypeFilter}
          onChange={(e) => { setEventTypeFilter(e.target.value); setPage(1); }}
          className="bg-[#080f23] text-white border border-slate-700 rounded p-2 text-sm px-4"
        />
      </div>

      {error && (
        <div className="bg-red-500/10 text-red-400 p-4 rounded mb-4">{error}</div>
      )}

      {loading ? (
        <div className="text-slate-500 flex justify-center py-12">Loading manufacturing events...</div>
      ) : events.length === 0 ? (
        <div className="text-slate-500 bg-[#080f23]/50 backdrop-blur-md p-12 rounded border border-slate-800 text-center">
          <p className="text-lg font-medium mb-2">No events found</p>
          <p className="text-sm">Try adjusting your filters or wait for new communications to be processed.</p>
        </div>
      ) : (
        <div className="bg-[#080f23]/50 backdrop-blur-md border border-slate-800 rounded overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-white/5 border-b border-slate-800 text-sm text-slate-300">
              <tr>
                <th className="p-4 font-medium">Event Type</th>
                <th className="p-4 font-medium">Description</th>
                <th className="p-4 font-medium">Severity</th>
                <th className="p-4 font-medium">Status</th>
                <th className="p-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {events.map((event) => (
                <tr key={event.id} className="border-b border-slate-800/50 last:border-0 hover:bg-white/5 transition-colors">
                  <td className="p-4 font-medium text-white">
                    {event.canonical_event_type || "?"}
                  </td>
                  <td className="p-4 text-slate-400 max-w-md truncate">
                    {event.description || "?"}
                  </td>
                  <td className="p-4">
                    <span className={`inline-block px-2.5 py-1 rounded-md text-xs font-semibold ${getSeverityColor(event.severity)}`}>
                      {event.severity || "Unknown"}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className={`inline-block px-2.5 py-1 rounded-md text-xs font-semibold ${getStatusColor(event.event_status)}`}>
                      {event.event_status}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <Link href={`/events/${event.id}`} className="text-cyan-400 hover:text-cyan-300 text-sm font-medium">
                      Investigate &rarr;
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          <div className="p-4 border-t border-slate-800 flex justify-between items-center text-sm text-slate-400">
            <div>
              Showing {((page - 1) * limit) + 1} to {Math.min(page * limit, total)} of {total}
            </div>
            <div className="flex space-x-2">
              <button 
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
                className="px-3 py-1 bg-white/5 hover:bg-white/10 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button 
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
                className="px-3 py-1 bg-white/5 hover:bg-white/10 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
