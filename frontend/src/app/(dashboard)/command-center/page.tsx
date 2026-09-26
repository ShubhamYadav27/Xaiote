'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAlerts, Alert } from '@/lib/alerts-api';
import { AlertDrawer } from '@/components/alerts/AlertDrawer';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';

export default function CommandCenterPage() {
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);

  const { data: alerts, isLoading, error } = useQuery({
    queryKey: ['alerts'],
    queryFn: getAlerts,
    // Refetch often since it's an operational dashboard
    refetchInterval: 30000,
  });

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'HIGH': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'MEDIUM': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'LOW': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'OPEN': return <AlertCircle className="h-4 w-4 text-red-400" />;
      case 'ACKNOWLEDGED': return <Clock className="h-4 w-4 text-amber-400" />;
      case 'RESOLVED': return <CheckCircle className="h-4 w-4 text-green-400" />;
      default: return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white tracking-tight">Command Center</h1>
      </div>

      <div className="bg-[#080f23]/60 border border-slate-700/50 rounded-xl overflow-hidden backdrop-blur-sm">
        <div className="px-6 py-4 border-b border-slate-700/50 flex justify-between items-center">
          <h2 className="text-lg font-medium text-slate-200">Active Alerts</h2>
          {isLoading && <span className="text-sm text-slate-400 animate-pulse">Refreshing...</span>}
        </div>

        {error ? (
          <div className="p-8 text-center text-red-400">Failed to load alerts.</div>
        ) : isLoading && !alerts ? (
          <div className="p-8 text-center text-slate-400">Loading alerts...</div>
        ) : alerts && alerts.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No active alerts found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="text-xs uppercase bg-slate-800/50 text-slate-400">
                <tr>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Severity</th>
                  <th className="px-6 py-3 font-medium">Title</th>
                  <th className="px-6 py-3 font-medium">Target</th>
                  <th className="px-6 py-3 font-medium">Created</th>
                  <th className="px-6 py-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {alerts?.map((alert: Alert) => (
                  <tr 
                    key={alert.id} 
                    className="hover:bg-slate-800/30 transition-colors group cursor-pointer"
                    onClick={() => setSelectedAlertId(alert.id)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(alert.status)}
                        <span className="font-medium text-slate-200">{alert.status}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${getSeverityColor(alert.severity)}`}>
                        {alert.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-200 mb-0.5">{alert.title}</div>
                      <div className="text-xs text-slate-500 truncate max-w-xs">{alert.message}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-slate-400">
                      {alert.entity_type} {alert.entity_id ? `(${alert.entity_id.substring(0, 8)}...)` : ''}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-slate-400">
                      {new Date(alert.created_at).toLocaleDateString()} {new Date(alert.created_at).toLocaleTimeString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedAlertId(alert.id);
                        }}
                        className="text-[var(--color-x-cyan)] hover:text-cyan-300 font-medium text-sm transition-colors"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedAlertId && (
        <AlertDrawer 
          alertId={selectedAlertId} 
          onClose={() => setSelectedAlertId(null)} 
        />
      )}
    </div>
  );
}
