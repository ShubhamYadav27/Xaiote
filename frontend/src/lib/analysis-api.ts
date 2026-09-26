import { fetchApi } from './api';

export interface Assessment {
  id: string;
  category: string;
  role: string;
  explanation: string;
  confidence: string; // HIGH, MEDIUM, LOW
  status: string; // PENDING, CONFIRMED, REJECTED
}

export interface AnalysisStatus {
  analysis_id: string;
  version: number;
  status: string; // PENDING, COMPLETED, FAILED
  is_stale: boolean;
  assessments?: Assessment[];
  decision_history?: any[];
}

export async function getAnalysis(incidentId: string): Promise<AnalysisStatus> {
  return fetchApi(`/analysis/incidents/${incidentId}`);
}

export async function generateAnalysis(incidentId: string, manualReanalysis: boolean): Promise<{ analysis_id: string; status: string; version: number }> {
  return fetchApi(`/analysis/incidents/${incidentId}/generate`, {
    method: 'POST',
    body: JSON.stringify({ incident_id: incidentId, manual_reanalysis: manualReanalysis }),
    headers: {
      'Idempotency-Key': crypto.randomUUID()
    }
  });
}

export async function confirmAssessment(analysisId: string, assessmentId: string, expectedRevision: number): Promise<{ assessment_id: string; status: string; revision: number }> {
  return fetchApi(`/analysis/${analysisId}/assessments/${assessmentId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ expected_revision: expectedRevision })
  });
}

export async function rejectAssessment(analysisId: string, assessmentId: string, expectedRevision: number, reason: string): Promise<{ assessment_id: string; status: string; revision: number }> {
  return fetchApi(`/analysis/${analysisId}/assessments/${assessmentId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ expected_revision: expectedRevision, reason })
  });
}
