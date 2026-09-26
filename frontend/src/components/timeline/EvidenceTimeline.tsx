import React from 'react';
import UncertaintyBadge from '../ui/UncertaintyBadge';

export default function EvidenceTimeline({ chain }: { chain: any }) {
    if (!chain) return <div>No evidence available.</div>;

    const stages = [
        { key: 'raw', label: 'Raw Communication' },
        { key: 'transcript', label: 'Transcript' },
        { key: 'extraction', label: 'Extraction' },
        { key: 'resolution', label: 'Entity Resolution' },
        { key: 'event', label: 'Manufacturing Event' },
        { key: 'impact', label: 'Work-Order Impact' },
        { key: 'risk', label: 'Risk Evaluation' },
        { key: 'incident', label: 'Incident' },
        { key: 'rca', label: 'RCA' },
        { key: 'alert', label: 'Alert' },
        { key: 'recommendation', label: 'Recommendation' },
        { key: 'approval', label: 'Approval' },
        { key: 'execution', label: 'Execution Attempt' },
        { key: 'outcome', label: 'External Outcome' },
        { key: 'recalculation', label: 'Risk Recalculation' }
    ];

    let terminated = false;

    return (
        <div className="flex flex-col space-y-2 border-l-2 border-gray-300 ml-4 pl-4 py-2">
            <h3 className="font-bold mb-2">Chronological Evidence Timeline</h3>
            {stages.map((stage) => {
                const node = chain[stage.key];
                if (terminated) return null; // Do not invent missing stages

                if (!node) {
                    // Check if it failed closed
                    if (chain.final_state === 'NEEDS_REVIEW' || chain.final_state === 'INSUFFICIENT_EVIDENCE') {
                        terminated = true;
                        return (
                            <div key="termination" className="mt-4 p-2 bg-gray-50 border border-gray-200 text-sm">
                                <span className="font-semibold text-gray-700">PROCESS TERMINATED SAFELY: </span>
                                <UncertaintyBadge status={chain.final_state} />
                            </div>
                        );
                    }
                    return <div key={stage.key} className="text-gray-400 text-sm italic">{stage.label} (Not reached)</div>;
                }

                return (
                    <div key={stage.key} className="flex items-center space-x-2">
                        <div className="w-2 h-2 rounded-full bg-blue-500 -ml-[1.35rem]"></div>
                        <span className="font-semibold text-sm w-32">{stage.label}:</span>
                        <span className="font-mono text-xs text-gray-600 truncate">{node.id || 'Present'}</span>
                        {node.status && <UncertaintyBadge status={node.status} />}
                    </div>
                );
            })}
        </div>
    );
}
