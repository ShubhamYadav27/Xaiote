import os

content = '''"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { fetchApi } from "@/lib/api";
import Link from "next/link";

export default function EventDetailPage() {
  const { id } = useParams();
  const router = useRouter();

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Revision Form State
  const [isRevising, setIsRevising] = useState(false);
  const [revisionChanges, setRevisionChanges] = useState<any>({});
  const [revisionReason, setRevisionReason] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    setLoading(true);
    try {
      const response = await fetchApi(`/events/${id}`);
      setData(response);
    } catch (e: any) {
      setError(e.message || "Failed to load event");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitRevision = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError("");
    
    // Clean empty changes
    const cleanedChanges: any = {};
    for (const key of Object.keys(revisionChanges)) {
      if (revisionChanges[key] !== undefined && revisionChanges[key] !== "") {
        cleanedChanges[key] = revisionChanges[key];
      }
    }

    if (Object.keys(cleanedChanges).length === 0) {
      setSubmitError("No fields changed.");
      return;
    }
    if (!revisionReason.trim()) {
      setSubmitError("Reason is required.");
      return;
    }

    setSubmitting(true);
    try {
      await fetchApi(`/events/${id}/revisions`, {
        method: "POST",
        body: JSON.stringify({
          changes: cleanedChanges,
          reason: revisionReason
        })
      });
      setIsRevising(false);
      setRevisionChanges({});
      setRevisionReason("");
      await loadData();
    } catch (err: any) {
      setSubmitError(err.message || "Failed to submit revision");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-8 text-slate-400 text-center">Loading operational intelligence...</div>;
  if (error) return <div className="p-8 text-red-400 bg-red-500/10 rounded m-8">{error}</div>;
  if (!data) return <div className="p-8 text-slate-400 text-center">Event not found.</div>;

  const { base_event, current_state, revisions, evidence } = data;

  const isAmbiguous = evidence?.entity_resolution?.overall_status === "REQUIRES_REVIEW" || 
                      current_state.event_status === "REQUIRES_REVIEW";

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <Link href="/events" className="text-cyan-400 hover:text-cyan-300 text-sm mb-4 inline-block">&larr; Back to Inbox</Link>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
            Event Investigation
            <span className="text-sm bg-slate-800 text-slate-300 px-3 py-1 rounded-full font-mono">{id}</span>
          </h1>
        </div>
        {isAmbiguous && (
          <div className="bg-amber-500/20 text-amber-400 border border-amber-500/50 px-4 py-2 rounded flex items-center gap-2 shadow-lg">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
            </span>
            <span className="font-semibold text-sm tracking-wide uppercase">Needs Confirmation</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Left Column: Lineage / Evidence */}
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-white border-b border-slate-800 pb-2">Original Evidence Chain</h2>
          
          {/* Communication Message */}
          <div className="bg-[#080f23]/50 border border-slate-800 rounded p-5 space-y-3">
            <div className="flex justify-between items-center text-xs text-slate-500 uppercase tracking-widest font-bold">
              <span>1. Raw Ingestion</span>
              <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">{evidence?.communication_message?.source_channel || "UNKNOWN"}</span>
            </div>
            {evidence?.communication_message ? (
              <div className="text-sm">
                <div className="text-slate-400 mb-2">Message ID: <span className="text-slate-300 font-mono">{evidence.communication_message.id}</span></div>
                <div className="p-3 bg-slate-900 rounded font-mono text-slate-300 break-all text-xs border border-slate-800/50">
                  {evidence.communication_message.raw_payload || "No text payload"}
                </div>
              </div>
            ) : (
              <div className="text-sm text-slate-500 italic">No communication message found.</div>
            )}
          </div>

          {/* Transcript */}
          <div className="bg-[#080f23]/50 border border-slate-800 rounded p-5 space-y-3">
            <div className="flex justify-between items-center text-xs text-slate-500 uppercase tracking-widest font-bold">
              <span>2. Audio Transcript</span>
              <span className="bg-blue-900/30 text-blue-400 px-2 py-0.5 rounded border border-blue-900/50">STT Model</span>
            </div>
            {evidence?.transcript ? (
              <div className="text-sm">
                <div className="text-slate-400 mb-2">Provider: <span className="text-slate-300 font-mono">{evidence.transcript.provider} / {evidence.transcript.model}</span></div>
                <div className="p-3 bg-blue-950/20 rounded text-slate-200 italic border border-blue-900/30">
                  &quot;{evidence.transcript.transcript || "Empty audio."}&quot;
                </div>
              </div>
            ) : (
              <div className="text-sm text-slate-500 italic">No transcript associated.</div>
            )}
          </div>

          {/* LLM Extraction */}
          <div className="bg-[#080f23]/50 border border-slate-800 rounded p-5 space-y-3">
            <div className="flex justify-between items-center text-xs text-slate-500 uppercase tracking-widest font-bold">
              <span>3. AI Extraction</span>
              <span className="bg-purple-900/30 text-purple-400 px-2 py-0.5 rounded border border-purple-900/50">LLM Output</span>
            </div>
            {evidence?.extraction ? (
              <div className="text-sm space-y-2">
                <div className="text-slate-400">Confidence: <span className="text-slate-300 font-mono">{evidence.extraction.extraction_confidence || 0}</span></div>
                <pre className="p-3 bg-slate-900 rounded font-mono text-slate-300 text-xs overflow-x-auto border border-slate-800/50">
                  {evidence.extraction.raw_response_payload 
                    ? JSON.stringify(evidence.extraction.raw_response_payload, null, 2) 
                    : "No extraction payload"}
                </pre>
              </div>
            ) : (
              <div className="text-sm text-slate-500 italic">No extraction data found.</div>
            )}
          </div>

          {/* Entity Resolution */}
          <div className="bg-[#080f23]/50 border border-slate-800 rounded p-5 space-y-3">
            <div className="flex justify-between items-center text-xs text-slate-500 uppercase tracking-widest font-bold">
              <span>4. Entity Resolution</span>
              <span className="bg-emerald-900/30 text-emerald-400 px-2 py-0.5 rounded border border-emerald-900/50">Database Graph</span>
            </div>
            {evidence?.entity_resolution ? (
              <div className="text-sm space-y-3">
                <div className="flex gap-4">
                  <div className="text-slate-400">Status: <span className="text-slate-300 font-bold">{evidence.entity_resolution.overall_status}</span></div>
                </div>
                
                {/* Ambiguity warnings */}
                {evidence.entity_resolution.machine_state === "AMBIGUOUS" && (
                  <div className="text-amber-400 bg-amber-500/10 p-2 rounded text-xs border border-amber-500/20">
                    &#9888; Machine reference is ambiguous. Needs human confirmation.
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 bg-slate-900 rounded border border-slate-800 text-slate-300">
                    <span className="text-slate-500 block mb-1">Machine ID</span>
                    <span className="font-mono">{evidence.entity_resolution.machine_id || "Unresolved"}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded border border-slate-800 text-slate-300">
                    <span className="text-slate-500 block mb-1">Plant ID</span>
                    <span className="font-mono">{evidence.entity_resolution.plant_id || "Unresolved"}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded border border-slate-800 text-slate-300">
                    <span className="text-slate-500 block mb-1">Work Order ID</span>
                    <span className="font-mono">{evidence.entity_resolution.work_order_id || "Unresolved"}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-sm text-slate-500 italic">No resolution data found.</div>
            )}
          </div>
        </div>

        {/* Right Column: Event State & Revisions */}
        <div className="space-y-6">
          <div className="flex justify-between items-end border-b border-slate-800 pb-2">
            <h2 className="text-xl font-bold text-white">Canonical State</h2>
            <button 
              onClick={() => setIsRevising(!isRevising)}
              className="text-xs bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 px-3 py-1 rounded transition-colors"
            >
              {isRevising ? "Cancel Revision" : "Submit Correction"}
            </button>
          </div>

          <div className="bg-slate-900/80 border border-slate-700 rounded-lg overflow-hidden shadow-xl">
            <div className="bg-slate-800/50 p-4 border-b border-slate-700 flex justify-between">
              <span className="text-slate-300 font-medium">Effective Data</span>
              <span className="text-xs px-2 py-1 bg-teal-500/20 text-teal-400 rounded">CONFIRMED FACT</span>
            </div>
            
            <div className="p-0">
              <table className="w-full text-sm text-left">
                <tbody>
                  {[
                    { label: "Status", key: "event_status" },
                    { label: "Type", key: "canonical_event_type" },
                    { label: "Severity", key: "severity" },
                    { label: "Root Cause", key: "root_cause" },
                    { label: "Downtime (min)", key: "reported_downtime_minutes" },
                    { label: "Quantity Affected", key: "quantity_affected" },
                    { label: "Time Reference", key: "event_time_reference" },
                    { label: "Description", key: "description" },
                  ].map((field, idx) => {
                    const val = current_state[field.key];
                    const prov = current_state[`${field.key}_provenance`];
                    return (
                      <tr key={field.key} className={idx % 2 === 0 ? "bg-white/[0.02]" : ""}>
                        <td className="p-3 font-medium text-slate-400 border-b border-slate-800 w-1/3">{field.label}</td>
                        <td className="p-3 text-slate-200 border-b border-slate-800">
                          <div className="flex justify-between items-center">
                            <span>{val !== null && val !== undefined ? String(val) : <span className="text-slate-600 italic">None</span>}</span>
                            {prov && (
                              <span className={`text-[10px] px-1.5 py-0.5 rounded ml-2 ${
                                prov === 'HUMAN_CONFIRMED' ? 'bg-cyan-500/20 text-cyan-400' :
                                prov === 'MODEL_DERIVED' ? 'bg-purple-500/20 text-purple-400' :
                                'bg-slate-700 text-slate-400'
                              }`}>
                                {prov}
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Revision Form */}
          {isRevising && (
            <div className="bg-[#080f23] border border-cyan-500/50 rounded-lg p-5 shadow-[0_0_15px_rgba(34,211,238,0.1)]">
              <h3 className="text-white font-bold mb-4 flex items-center gap-2">
                <span className="text-cyan-400">?</span> Human Correction
              </h3>
              <form onSubmit={handleSubmitRevision} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Severity</label>
                    <select 
                      className="w-full bg-slate-900 border border-slate-700 text-white text-sm rounded p-2 focus:border-cyan-500 outline-none"
                      value={revisionChanges.severity || ""}
                      onChange={(e) => setRevisionChanges({...revisionChanges, severity: e.target.value})}
                    >
                      <option value="">(No change)</option>
                      <option value="CRITICAL">CRITICAL</option>
                      <option value="HIGH">HIGH</option>
                      <option value="MEDIUM">MEDIUM</option>
                      <option value="LOW">LOW</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Event Type</label>
                    <input 
                      type="text"
                      className="w-full bg-slate-900 border border-slate-700 text-white text-sm rounded p-2 focus:border-cyan-500 outline-none"
                      placeholder="e.g. BREAKDOWN"
                      value={revisionChanges.canonical_event_type || ""}
                      onChange={(e) => setRevisionChanges({...revisionChanges, canonical_event_type: e.target.value})}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Root Cause</label>
                    <input 
                      type="text"
                      className="w-full bg-slate-900 border border-slate-700 text-white text-sm rounded p-2 focus:border-cyan-500 outline-none"
                      value={revisionChanges.root_cause || ""}
                      onChange={(e) => setRevisionChanges({...revisionChanges, root_cause: e.target.value})}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Downtime (min)</label>
                    <input 
                      type="number"
                      className="w-full bg-slate-900 border border-slate-700 text-white text-sm rounded p-2 focus:border-cyan-500 outline-none"
                      value={revisionChanges.reported_downtime_minutes || ""}
                      onChange={(e) => setRevisionChanges({...revisionChanges, reported_downtime_minutes: e.target.value ? parseInt(e.target.value) : ""})}
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Reason for correction (Required)</label>
                  <input 
                    type="text"
                    required
                    className="w-full bg-slate-900 border border-slate-700 text-white text-sm rounded p-2 focus:border-cyan-500 outline-none"
                    placeholder="e.g. LLM misidentified severity"
                    value={revisionReason}
                    onChange={(e) => setRevisionReason(e.target.value)}
                  />
                </div>

                {submitError && <div className="text-red-400 text-sm bg-red-500/10 p-2 rounded">{submitError}</div>}

                <div className="flex justify-end gap-3 pt-2">
                  <button 
                    type="button" 
                    onClick={() => setIsRevising(false)}
                    className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit" 
                    disabled={submitting}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-bold rounded shadow-lg disabled:opacity-50"
                  >
                    {submitting ? "Applying..." : "Save Revision"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Revision History */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-2">Audit Trail</h3>
            
            {revisions.length === 0 ? (
              <div className="text-sm text-slate-500 italic p-4 bg-[#080f23]/50 rounded border border-slate-800">
                No human revisions have been made.
              </div>
            ) : (
              <div className="space-y-3">
                {revisions.map((rev: any, idx: number) => (
                  <div key={idx} className="p-4 bg-slate-900/50 rounded-lg border border-slate-800 text-sm">
                    <div className="flex justify-between items-start mb-3 border-b border-slate-800/50 pb-2">
                      <div className="font-bold text-cyan-400">Human Correction</div>
                      <div className="text-slate-500 text-xs">{new Date(rev.revision_timestamp).toLocaleString()}</div>
                    </div>
                    
                    <div className="text-slate-300 italic mb-3">"{rev.reason}"</div>
                    
                    <div className="grid grid-cols-1 gap-2">
                      {Object.entries(rev.changed_fields).map(([field, diff]: [string, any]) => (
                        <div key={field} className="flex items-center gap-3 bg-slate-950 p-2 rounded border border-slate-800/80">
                          <span className="text-slate-400 font-medium w-32">{field}:</span>
                          <span className="text-red-400/80 line-through">{diff.old_value || "None"}</span>
                          <span className="text-slate-600">&rarr;</span>
                          <span className="text-green-400">{diff.new_value || "None"}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
'''

with open('frontend/src/app/(dashboard)/events/[id]/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
