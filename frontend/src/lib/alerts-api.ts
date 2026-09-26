import { fetchApi } from './api';

export interface AlertHistory {
  id: string;
  alert_id: string;
  from_status: string;
  to_status: string;
  changed_by_user_id: string | null;
  changed_at: string;
  notes: string | null;
}

export interface Alert {
  id: string;
  type: string;
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: string | null;
  plant_id: string | null;
  originating_policy_id: string | null;
  originating_policy_version: number | null;
  version: number;
  created_at: string;
  updated_at: string;
  history?: AlertHistory[];
}

export interface AlertEnvelope {
  data: Alert;
}

export interface AlertListEnvelope {
  data: Alert[];
}

export interface TransitionPayload {
  status: 'ACKNOWLEDGED' | 'RESOLVED';
  expected_version: number;
  plant_id: string | null;
}

export async function getAlerts(): Promise<Alert[]> {
  return fetchApi('/alerts');
}

export async function getAlert(alertId: string): Promise<Alert> {
  return fetchApi(`/alerts/${alertId}`);
}

export async function transitionAlert(alertId: string, payload: TransitionPayload): Promise<Alert> {
  return fetchApi(`/alerts/${alertId}/transition`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
