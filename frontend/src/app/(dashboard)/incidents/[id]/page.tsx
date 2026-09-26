"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import { AlertCircle, CheckCircle2, Link as LinkIcon, Unlink } from "lucide-react";

interface IncidentDetail {
  incident: {
    id: string;
    title: string;
    status: "ACTIVE" | "RESOLVED";
    created_at: string;
  };
  linked_events: any[];
  impacts: any[];
  decision_history: any[];
}

export default function IncidentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [data, setData] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState(false);
  const [resolveResult, setResolveResult] = useState<any | null>(null);

  useEffect(() => {
    loadDetail();
  }, [params.id]);

  async function loadDetail() {
    try {
      setLoading(true);
      const res = await fetchApi(`/incidents/${params.id}`);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load incident details");
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve() {
    if (!confirm("Are you sure you want to mark this incident as resolved? This will clear active risk for affected work orders.")) return;
    
    try {
      setResolving(true);
      const res = await fetchApi(`/incidents/${params.id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ reason: "Manual resolution" })
      });
      setResolveResult(res.risk_changes);
      await loadDetail();
    } catch (err: any) {
      alert("Failed to resolve: " + err.message);
    } finally {
      setResolving(false);
    }
  }

  if (loading) return <div className="p-8 text-center text-gray-500">Loading incident detail...</div>;
  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;
  if (!data) return null;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/incidents" className="text-indigo-600 hover:underline mb-2 inline-block text-sm">
            &larr; Back to Incidents
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Incident: {data.incident.title}
          </h1>
          <div className="flex items-center gap-3 mt-2">
            {data.incident.status === "ACTIVE" ? (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                <AlertCircle className="w-3 h-3 mr-1" /> ACTIVE
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                <CheckCircle2 className="w-3 h-3 mr-1" /> RESOLVED
              </span>
            )}
            <span className="text-sm text-gray-500">ID: {data.incident.id}</span>
          </div>
        </div>

        <div className="flex gap-2">
          <Link 
            href={`/incidents/${params.id}/investigation`}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg"
          >
            Root Cause Investigation
          </Link>
          {data.incident.status === "ACTIVE" && (
            <button
              onClick={handleResolve}
              disabled={resolving}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg disabled:opacity-50"
            >
              {resolving ? "Resolving..." : "Confirm Recovery"}
            </button>
          )}
        </div>
      </div>

      {resolveResult && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <h3 className="text-green-800 font-medium">Incident resolved. Risk re-evaluated for {resolveResult.length} affected Work Orders.</h3>
          <ul className="mt-2 text-sm text-green-700 list-disc pl-5">
            {resolveResult.map((change: any, i: number) => (
              <li key={i}>Work Order {change.work_order_id.split("-")[0]}: {change.previous_state} &rarr; {change.new_state}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Linked Events */}
        <div className="bg-white dark:bg-gray-800 border rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <LinkIcon className="w-4 h-4 text-gray-400" />
            Correlated Events
          </h2>
          <div className="space-y-3">
            {data.linked_events.map(ev => (
              <div key={ev.id} className="p-3 border rounded-lg hover:border-indigo-300">
                <Link href={`/events/${ev.id}`} className="text-sm font-medium text-indigo-600 block mb-1">
                  Event {ev.id.split("-")[0]}...
                </Link>
                <div className="text-xs text-gray-500">
                  Type: {ev.canonical_event_type} <br/>
                  Severity: {ev.severity}
                </div>
              </div>
            ))}
            {data.linked_events.length === 0 && <p className="text-sm text-gray-500">No linked events.</p>}
          </div>
        </div>

        {/* Affected Impacts */}
        <div className="bg-white dark:bg-gray-800 border rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-4">Affected Impacts</h2>
          <div className="space-y-3">
            {data.impacts.map(impact => (
              <div key={impact.id} className="p-3 border rounded-lg text-sm">
                <div className="flex justify-between font-medium">
                  <span>WO: {impact.work_order_id.split("-")[0]}...</span>
                  <span className={impact.status === 'CONFIRMED' ? 'text-red-600' : 'text-orange-500'}>
                    {impact.status}
                  </span>
                </div>
                <div className="text-xs text-gray-500 mt-1">Prov: {impact.provenance}</div>
              </div>
            ))}
            {data.impacts.length === 0 && <p className="text-sm text-gray-500">No associated impacts.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
