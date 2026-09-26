"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AlertCircle, AlertTriangle, CheckCircle, XCircle, RefreshCw } from "lucide-react";
import { 
  getAnalysis, 
  generateAnalysis, 
  confirmAssessment, 
  rejectAssessment,
  AnalysisStatus,
  Assessment
} from "@/lib/analysis-api";

export default function InvestigationPage() {
  const params = useParams();
  const router = useRouter();
  
  const [analysis, setAnalysis] = useState<AnalysisStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [activeRejectId, setActiveRejectId] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const incidentId = params.id as string;

  useEffect(() => {
    loadAnalysis();
  }, [incidentId]);

  async function loadAnalysis() {
    try {
      setLoading(true);
      setError(null);
      const res = await getAnalysis(incidentId);
      setAnalysis(res);
    } catch (err: any) {
      if (err.message && err.message.includes("404")) {
        // No analysis yet
        setAnalysis(null);
      } else {
        setError(err.message || "Failed to load analysis");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerate(manualReanalysis: boolean = false) {
    try {
      setGenerating(true);
      setError(null);
      await generateAnalysis(incidentId, manualReanalysis);
      await loadAnalysis();
    } catch (err: any) {
      setError(err.message || "Failed to generate analysis");
    } finally {
      setGenerating(false);
    }
  }

  async function handleConfirm(assessmentId: string) {
    if (!analysis) return;
    try {
      setProcessingId(assessmentId);
      await confirmAssessment(analysis.analysis_id, assessmentId, analysis.version);
      await loadAnalysis();
    } catch (err: any) {
      alert("Failed to confirm: " + err.message);
    } finally {
      setProcessingId(null);
    }
  }

  async function handleReject(assessmentId: string) {
    if (!analysis) return;
    if (!rejectReason.trim()) {
      alert("Please provide a reason for rejection");
      return;
    }
    try {
      setProcessingId(assessmentId);
      await rejectAssessment(analysis.analysis_id, assessmentId, analysis.version, rejectReason);
      setActiveRejectId(null);
      setRejectReason("");
      await loadAnalysis();
    } catch (err: any) {
      alert("Failed to reject: " + err.message);
    } finally {
      setProcessingId(null);
    }
  }

  if (loading) return <div className="p-8 text-center text-gray-500">Loading analysis...</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href={`/incidents/${incidentId}`} className="text-indigo-600 hover:underline mb-2 inline-block text-sm">
            &larr; Back to Incident
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Root Cause Investigation
          </h1>
          <p className="text-sm text-gray-500 mt-1">Incident ID: {incidentId}</p>
        </div>
        
        {!analysis && !loading && (
          <button
            onClick={() => handleGenerate(false)}
            disabled={generating}
            className="flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg disabled:opacity-50"
          >
            {generating ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : null}
            Generate Analysis
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 border border-red-200 rounded-lg">
          {error}
        </div>
      )}

      {analysis && (
        <div className="space-y-6">
          {/* Status Header */}
          <div className="bg-white dark:bg-gray-800 border rounded-xl p-5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <p className="text-sm text-gray-500">Analysis Status</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    analysis.status === 'COMPLETED' ? 'bg-green-100 text-green-800' : 
                    analysis.status === 'FAILED' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {analysis.status}
                  </span>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Version: {analysis.version}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={() => handleGenerate(true)}
              disabled={generating}
              className="flex items-center px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium rounded-lg disabled:opacity-50 text-sm"
            >
              {generating ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
              Re-analyze
            </button>
          </div>

          {analysis.is_stale && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start">
              <AlertTriangle className="w-5 h-5 text-yellow-600 mr-3 mt-0.5" />
              <div>
                <h3 className="text-yellow-800 font-medium">Stale — Newer Evidence Available</h3>
                <p className="text-yellow-700 text-sm mt-1">
                  New events or topology changes have occurred since this analysis was generated. Consider running a re-analysis.
                </p>
              </div>
            </div>
          )}

          {/* Assessments */}
          <div>
            <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Root Cause Candidates</h2>
            {(!analysis.assessments || analysis.assessments.length === 0) ? (
              <p className="text-gray-500 text-sm italic">No candidates identified or analysis is still pending.</p>
            ) : (
              <div className="space-y-4">
                {analysis.assessments.map(assessment => (
                  <div key={assessment.id} className="bg-white dark:bg-gray-800 border rounded-xl p-5 shadow-sm">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs font-semibold rounded uppercase">
                            {assessment.category}
                          </span>
                          <span className="px-2 py-1 bg-indigo-50 text-indigo-700 text-xs font-semibold rounded uppercase">
                            {assessment.role}
                          </span>
                          <span className={`px-2 py-1 text-xs font-semibold rounded uppercase ${
                            assessment.confidence === 'HIGH' ? 'bg-green-100 text-green-700' :
                            assessment.confidence === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'
                          }`}>
                            {assessment.confidence} CONFIDENCE
                          </span>
                        </div>
                        <p className="text-sm text-gray-500 font-mono mt-2">ID: {assessment.id}</p>
                      </div>
                      
                      <div className="flex flex-col items-end gap-2">
                        <span className={`flex items-center text-sm font-medium ${
                          assessment.status === 'CONFIRMED' ? 'text-green-600' :
                          assessment.status === 'REJECTED' ? 'text-red-600' : 'text-gray-500'
                        }`}>
                          {assessment.status === 'CONFIRMED' && <CheckCircle className="w-4 h-4 mr-1" />}
                          {assessment.status === 'REJECTED' && <XCircle className="w-4 h-4 mr-1" />}
                          {assessment.status === 'PENDING' && <AlertCircle className="w-4 h-4 mr-1" />}
                          {assessment.status}
                        </span>
                      </div>
                    </div>
                    
                    <div className="mb-4 text-gray-700 dark:text-gray-300">
                      {assessment.explanation}
                    </div>

                    {assessment.status === 'PENDING' && (
                      <div className="border-t pt-4 flex gap-3">
                        <button
                          onClick={() => handleConfirm(assessment.id)}
                          disabled={processingId === assessment.id}
                          className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
                        >
                          Confirm
                        </button>
                        <button
                          onClick={() => setActiveRejectId(assessment.id)}
                          disabled={processingId === assessment.id}
                          className="px-4 py-2 bg-red-50 text-red-700 hover:bg-red-100 text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
                        >
                          Reject...
                        </button>
                      </div>
                    )}

                    {activeRejectId === assessment.id && assessment.status === 'PENDING' && (
                      <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Reason for rejection
                        </label>
                        <textarea
                          value={rejectReason}
                          onChange={(e) => setRejectReason(e.target.value)}
                          className="w-full border rounded p-2 text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none"
                          rows={3}
                          placeholder="Provide evidence or context for why this is not the root cause..."
                        />
                        <div className="flex gap-2 mt-3">
                          <button
                            onClick={() => handleReject(assessment.id)}
                            disabled={!rejectReason.trim() || processingId === assessment.id}
                            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg disabled:opacity-50"
                          >
                            Submit Rejection
                          </button>
                          <button
                            onClick={() => {
                              setActiveRejectId(null);
                              setRejectReason("");
                            }}
                            className="px-4 py-2 bg-white border hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-lg"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Decision History */}
          {analysis.decision_history && analysis.decision_history.length > 0 && (
            <div className="bg-white dark:bg-gray-800 border rounded-xl p-5 mt-6">
              <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Decision History</h2>
              <div className="space-y-3">
                {analysis.decision_history.map((hist, idx) => (
                  <div key={idx} className="text-sm border-l-2 border-gray-200 pl-4 py-1">
                    <p className="font-medium text-gray-800 dark:text-gray-200">
                      {hist.action} on Assessment {hist.assessment_id?.split('-')[0]}...
                    </p>
                    <p className="text-gray-500 mt-1">
                      {hist.reason || 'No reason provided.'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
