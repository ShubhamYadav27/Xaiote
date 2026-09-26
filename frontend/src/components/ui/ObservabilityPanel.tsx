import React from 'react';

export default function ObservabilityPanel({ metadata }: { metadata: any }) {
    if (!metadata) return null;
    return (
        <div className="bg-slate-900 text-green-400 font-mono text-xs p-4 rounded-md mt-4 overflow-auto">
            <div className="text-white mb-2 uppercase tracking-wide border-b border-slate-700 pb-1">Engineering Observability</div>
            <div className="grid grid-cols-2 gap-2">
                <div>Correlation ID: <span className="text-gray-300">{metadata.correlation_id}</span></div>
                <div>AI Provider: <span className="text-gray-300">{metadata.provider}</span></div>
                <div>Model: <span className="text-gray-300">{metadata.model}</span></div>
                <div>Prompt Schema V: <span className="text-gray-300">{metadata.schema_version}</span></div>
                <div>Extraction Conf: <span className="text-gray-300">{metadata.extraction_confidence}%</span></div>
            </div>
            <div className="mt-2 text-gray-500 italic">Sensitive tokens scrubbed by Phase 5H logger.</div>
        </div>
    );
}
