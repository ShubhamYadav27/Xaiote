'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAlert, transitionAlert, Alert } from '@/lib/alerts-api';
import { getOperationalContextForWorkOrder } from '@/lib/operational-context-api';
import { OperationalTimeline } from '@/components/timeline/OperationalTimeline';
import { useAuth } from '@/components/providers/AuthProvider';
import { X, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { useState } from 'react';

interface AlertDrawerProps {
  alertId: string | null;
  onClose: () => void;
}

export function AlertDrawer({ alertId, onClose }: AlertDrawerProps) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [transitionError, setTransitionError] = useState<string | null>(null);

  const { data: alert, isLoading, error } = useQuery({
    queryKey: ['alert', alertId],
    queryFn: () => getAlert(alertId!),
    enabled: !!alertId,
  });

  const { data: opContext } = useQuery({
    queryKey: ['operational-context', alert?.entity_id],
    queryFn: () => getOperationalContextForWorkOrder(alert?.entity_id || ''),
    enabled: !!alert && alert.entity_type === 'work_order' && !!alert.entity_id,
  });

  const transitionMutation = useMutation({
    mutationFn: ({ status, expectedVersion, plantId }: { status: 'ACKNOWLEDGED' | 'RESOLVED', expectedVersion: number, plantId: string | null }) => 
      transitionAlert(alertId!, { status, expected_version: expectedVersion, plant_id: plantId }),
    onSuccess: (updatedAlert) => {
      queryClient.setQueryData(['alert', alertId], updatedAlert);
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setTransitionError(null);
    },
    onError: (err: any) => {
      if (err.message?.includes('409') || err.message?.toLowerCase().includes('conflict')) {
        setTransitionError("Stale alert / state changed. Please refresh.");
      } else {
        setTransitionError(err.message || "Failed to transition alert.");
      }
    }
  });

  if (!alertId) return null;

  const isViewer = (user as any)?.role === 'VIEWER';

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full md:w-[600px] bg-[#080f23] border-l border-slate-700 shadow-2xl flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-slate-700 bg-slate-900/50">
        <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          Alert Details
        </h2>
        <button onClick={onClose} className="p-2 text-slate-400 hover:text-white rounded-md hover:bg-slate-800 transition-colors">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-8">
        {isLoading ? (
          <div className="text-slate-400 animate-pulse">Loading alert details...</div>
        ) : error ? (
          <div className="text-red-400 bg-red-950/30 p-4 rounded-md border border-red-900/50">
            Failed to load alert details.
          </div>
        ) : alert ? (
          <>
            {/* Header / Basic Info */}
            <div className="space-y-4">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">{alert.title}</h3>
                <p className="text-slate-300">{alert.message}</p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                  <div className="text-slate-500 mb-1">Status</div>
                  <div className="font-medium text-slate-200">{alert.status}</div>
                </div>
                <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                  <div className="text-slate-500 mb-1">Severity</div>
                  <div className="font-medium text-slate-200">{alert.severity}</div>
                </div>
                <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                  <div className="text-slate-500 mb-1">Created At</div>
                  <div className="font-medium text-slate-200">{new Date(alert.created_at).toLocaleString()}</div>
                </div>
                <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                  <div className="text-slate-500 mb-1">Provenance</div>
                  <div className="font-medium text-slate-200">
                    Policy: {alert.originating_policy_id || 'N/A'} (v{alert.originating_policy_version || '?'})
                  </div>
                </div>
              </div>
            </div>

            {/* Actions */}
            {!isViewer && (
              <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700 space-y-3">
                <h4 className="text-sm font-medium text-slate-300 mb-2">Actions</h4>
                {transitionError && (
                  <div className="text-sm text-red-400 bg-red-950/50 p-2 rounded border border-red-900 flex items-center gap-2">
                    <Info className="h-4 w-4" />
                    {transitionError}
                  </div>
                )}
                <div className="flex gap-3">
                  <button
                    onClick={() => transitionMutation.mutate({ status: 'ACKNOWLEDGED', expectedVersion: alert.version, plantId: alert.plant_id })}
                    disabled={alert.status !== 'OPEN' || transitionMutation.isPending}
                    className="flex-1 bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 disabled:opacity-50 disabled:cursor-not-allowed border border-amber-500/20 py-2 rounded-md font-medium transition-colors"
                  >
                    {transitionMutation.isPending && transitionMutation.variables?.status === 'ACKNOWLEDGED' ? 'Processing...' : 'Acknowledge'}
                  </button>
                  <button
                    onClick={() => transitionMutation.mutate({ status: 'RESOLVED', expectedVersion: alert.version, plantId: alert.plant_id })}
                    disabled={alert.status === 'RESOLVED' || transitionMutation.isPending}
                    className="flex-1 bg-green-500/10 text-green-500 hover:bg-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed border border-green-500/20 py-2 rounded-md font-medium transition-colors"
                  >
                    {transitionMutation.isPending && transitionMutation.variables?.status === 'RESOLVED' ? 'Processing...' : 'Resolve'}
                  </button>
                </div>
              </div>
            )}

            {/* Target Context */}
            {alert.entity_type === 'work_order' && alert.entity_id && (
              <div>
                <h4 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Target Work Order Context</h4>
                <div className="bg-slate-800/30 p-4 rounded-lg border border-slate-700">
                  {opContext ? (
                    <div className="space-y-2 text-sm text-slate-300">
                      <div><span className="text-slate-500">ID:</span> {opContext.work_order_id}</div>
                      <div><span className="text-slate-500">Status:</span> {opContext.status}</div>
                      <div><span className="text-slate-500">Product:</span> {opContext.product_id || 'N/A'}</div>
                    </div>
                  ) : (
                    <div className="text-sm text-slate-500">Loading context...</div>
                  )}
                </div>
              </div>
            )}

            {/* Operational Timeline */}
            {alert.entity_type === 'work_order' && alert.entity_id && (
              <div>
                <h4 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Operational Timeline</h4>
                <div className="bg-slate-800/30 p-4 rounded-lg border border-slate-700">
                  <OperationalTimeline entityType={alert.entity_type} entityId={alert.entity_id} />
                </div>
              </div>
            )}

            {/* Alert History */}
            {alert.history && alert.history.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Alert History</h4>
                <div className="space-y-3">
                  {alert.history.map((h, idx) => (
                    <div key={h.id || idx} className="bg-slate-800/30 p-3 rounded border border-slate-700 text-sm">
                      <div className="flex justify-between text-slate-400 mb-1">
                        <span>{h.from_status} &rarr; {h.to_status}</span>
                        <span className="text-xs">{new Date(h.changed_at).toLocaleString()}</span>
                      </div>
                      {h.notes && <div className="text-slate-300 mt-2">{h.notes}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}
