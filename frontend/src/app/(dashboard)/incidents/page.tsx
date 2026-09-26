"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import { AlertCircle, CheckCircle2 } from "lucide-react";

interface Incident {
  id: string;
  title: string;
  status: "ACTIVE" | "RESOLVED";
  created_at: string;
  resolved_at: string | null;
  machine_id: string | null;
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadIncidents();
  }, []);

  async function loadIncidents() {
    try {
      setLoading(true);
      const data = await fetchApi("/incidents?limit=50");
      setIncidents(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || "Failed to load incidents");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Active Incidents</h1>
          <p className="text-sm text-gray-500 mt-1">Correlation of related manufacturing events</p>
        </div>
        <div className="text-sm font-medium text-gray-500">
          Total: {total}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-600 rounded-lg">{error}</div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading incidents...</div>
        ) : incidents.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No incidents found.</div>
        ) : (
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 dark:bg-gray-900/50 text-gray-500">
              <tr>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Title</th>
                <th className="px-6 py-4 font-medium">Created</th>
                <th className="px-6 py-4 font-medium">Resolved</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {incidents.map((incident) => (
                <tr key={incident.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4">
                    {incident.status === "ACTIVE" ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                        <AlertCircle className="w-3 h-3 mr-1" /> ACTIVE
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                        <CheckCircle2 className="w-3 h-3 mr-1" /> RESOLVED
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 font-medium">{incident.title}</td>
                  <td className="px-6 py-4 text-gray-500">{new Date(incident.created_at).toLocaleString()}</td>
                  <td className="px-6 py-4 text-gray-500">{incident.resolved_at ? new Date(incident.resolved_at).toLocaleString() : "-"}</td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      href={`/incidents/${incident.id}`}
                      className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 font-medium"
                    >
                      Investigate &rarr;
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
