"use client";
import React, { useState, useEffect } from 'react';

export default function CandidatesReviewPage() {
    const [candidates, setCandidates] = useState<any[]>([]);
    const [plants, setPlants] = useState<any[]>([]);
    const [machines, setMachines] = useState<any[]>([]);
    
    const [resolutions, setResolutions] = useState<Record<string, { plant_id: string, machine_id: string }>>({});
    
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [successMsg, setSuccessMsg] = useState<string | null>(null);

    const fetchData = async () => {
        try {
            const resCands = await fetch('/api/v1/candidates/pending');
            const dataCands = await resCands.json();
            setCandidates(dataCands || []);

            const resPlants = await fetch('/api/v1/plants');
            const dataPlants = await resPlants.json();
            setPlants(dataPlants.data?.items || []);

            const resMachines = await fetch('/api/v1/machines');
            const dataMachines = await resMachines.json();
            setMachines(dataMachines.data?.items || []);
        } catch (e) {
            console.error("Failed to fetch", e);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleSelectChange = (candId: string, field: 'plant_id' | 'machine_id', value: string) => {
        setResolutions(prev => ({
            ...prev,
            [candId]: {
                ...prev[candId],
                [field]: value
            }
        }));
    };

    const handleResolve = async (id: string) => {
        if (isSubmitting) return;
        setIsSubmitting(true);
        setErrorMsg(null);
        setSuccessMsg(null);
        
        const resolution = resolutions[id] || { plant_id: '', machine_id: '' };
        
        try {
            const res = await fetch(`/api/v1/candidates/${id}/resolve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plant_id: resolution.plant_id || null,
                    machine_id: resolution.machine_id || null
                })
            });
            
            if (!res.ok) {
                const text = await res.text();
                setErrorMsg(`An error occurred: ${text}`);
            } else {
                setSuccessMsg("Candidate resolved successfully.");
                fetchData();
            }
        } catch (e) {
            setErrorMsg("Network error.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-4">Pending Event Candidates (Human Review)</h1>
            {errorMsg && <div className="bg-red-100 text-red-700 p-3 mb-4 rounded">{errorMsg}</div>}
            {successMsg && <div className="bg-green-100 text-green-700 p-3 mb-4 rounded">{successMsg}</div>}

            {candidates.length === 0 ? (
                <p className="text-gray-500">No candidates require review at this time.</p>
            ) : (
                <div className="space-y-6">
                    {candidates.map((cand) => (
                        <div key={cand.id} className="border p-4 rounded shadow-sm bg-white">
                            <h3 className="font-semibold text-lg">Candidate: {cand.id}</h3>
                            <div className="mt-2 text-sm text-gray-700">
                                <p><strong>Status:</strong> <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded">{cand.processing_status}</span></p>
                                <p className="mt-2"><strong>Extracted Event Type:</strong> {cand.payload.event_type}</p>
                                <p><strong>Extracted Description:</strong> {cand.payload.event_description}</p>
                                <p><strong>Extracted Severity:</strong> {cand.payload.severity}</p>
                            </div>
                            
                            <div className="mt-4 border-t pt-4">
                                <h4 className="font-semibold mb-2">Entity Resolution Mapping</h4>
                                <div className="flex gap-4">
                                    <div>
                                        <label className="block text-sm mb-1">Plant</label>
                                        <select 
                                            className="border rounded p-2"
                                            value={resolutions[cand.id]?.plant_id || ''}
                                            onChange={(e) => handleSelectChange(cand.id, 'plant_id', e.target.value)}
                                        >
                                            <option value="">Select Plant...</option>
                                            {plants.map(p => (
                                                <option key={p.id} value={p.id}>{p.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm mb-1">Machine</label>
                                        <select 
                                            className="border rounded p-2"
                                            value={resolutions[cand.id]?.machine_id || ''}
                                            onChange={(e) => handleSelectChange(cand.id, 'machine_id', e.target.value)}
                                        >
                                            <option value="">Select Machine...</option>
                                            {machines.map(m => (
                                                <option key={m.id} value={m.id}>{m.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                                <button 
                                    onClick={() => handleResolve(cand.id)} 
                                    disabled={isSubmitting}
                                    className={`mt-4 px-4 py-2 rounded text-white ${isSubmitting ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'}`}
                                >
                                    {isSubmitting ? 'Processing...' : 'Submit Resolution'}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
