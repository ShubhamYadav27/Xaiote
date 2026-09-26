'use client';

import { useQuery } from '@tanstack/react-query';
import { getTimeline } from '@/lib/timeline-api';

export function OperationalTimeline({ entityType, entityId }: { entityType: string; entityId: string }) {
  const { data: timeline, isLoading, error } = useQuery({
    queryKey: ['timeline', entityType, entityId],
    queryFn: () => getTimeline(entityType, entityId),
    enabled: !!entityType && !!entityId,
  });

  if (isLoading) return <div className="text-slate-400 p-4">Loading timeline...</div>;
  if (error) return <div className="text-red-400 p-4">Failed to load timeline</div>;
  if (!timeline || !timeline.events || timeline.events.length === 0) {
    return <div className="text-slate-500 p-4">No events found for this entity.</div>;
  }

  return (
    <div className="space-y-4">
      {timeline.events.map((event, index) => (
        <div key={event.id || index} className="relative pl-6 border-l border-slate-700 pb-4 last:border-l-0 last:pb-0">
          <div className="absolute left-[-5px] top-1 w-2.5 h-2.5 rounded-full bg-[var(--color-x-cyan)] ring-4 ring-[#080f23]"></div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-slate-400 font-mono">
              {new Date(event.timestamp).toLocaleString()}
            </span>
            <span className="text-sm font-medium text-slate-200">
              {event.event_type}
            </span>
            <span className="text-sm text-slate-400">
              {event.description}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
