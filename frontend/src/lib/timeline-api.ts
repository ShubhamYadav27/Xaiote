import { fetchApi } from './api';

export interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type: string;
  description: string;
  source: string;
  metadata?: Record<string, any>;
}

export interface TimelineResponse {
  entity_type: string;
  entity_id: string;
  events: TimelineEvent[];
}

export async function getTimeline(entityType: string, entityId: string): Promise<TimelineResponse> {
  // Assuming timeline endpoint returns { data: TimelineResponse } based on fetchApi
  return fetchApi(`/timeline?entity_type=${entityType}&entity_id=${entityId}`);
}
