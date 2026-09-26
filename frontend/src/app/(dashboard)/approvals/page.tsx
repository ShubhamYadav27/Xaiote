"use client";
import React, { useState, useEffect } from 'react';

export default function ApprovalsPage() {
    const [actions, setActions] = useState<any[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    
    const fetchActions = () => {
        fetch('/api/v1/actions?status=PENDING_APPROVAL')
            .then(res => res.json())
            .then(data => setActions(data.data || []));
    };

    useEffect(() => {
        fetchActions();
    }, []);

    const handleApprove = async (id: string) => {
        if (isSubmitting) return;
        setIsSubmitting(true);
        setErrorMsg(null);
        try {
            const res = await fetch(`/api/v1/actions/${id}/approve`, { method: 'POST' });
            if (res.status === 409) {
                setErrorMsg("Conflict: This action has already been approved or modified by another user.");
                fetchActions(); // Refresh authoritative state
            } else if (!res.ok) {
                setErrorMsg("An error occurred during approval.");
            } else {
                setActions(actions.filter((a: any) => a.id !== id));
            }
        } catch (e) {
            setErrorMsg("Network error during approval.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-4">Pending Approvals</h1>
            {errorMsg && <div className="bg-red-100 text-red-700 p-2 rounded mb-4">{errorMsg}</div>}
            <div className="grid gap-4">
                {actions.length === 0 ? (
                    <p className="text-gray-500">No pending actions require approval.</p>
                ) : actions.map((action: any) => (
                    <div key={action.id} className="border p-4 rounded shadow-sm bg-white">
                        <h3 className="font-semibold">{action.action_type}</h3>
                        <p className="text-sm text-gray-600">Target: {action.target_work_order_id}</p>
                        <p className="text-sm text-gray-600 mb-4">Reason: {action.reasoning}</p>
                        <div className="flex gap-2">
                            <button 
                                onClick={() => handleApprove(action.id)} 
                                disabled={isSubmitting}
                                className={`px-4 py-2 rounded text-white ${isSubmitting ? 'bg-gray-400' : 'bg-blue-600'}`}>
                                {isSubmitting ? 'Processing...' : 'Approve & Execute'}
                            </button>
                            <button disabled={isSubmitting} className="bg-red-600 text-white px-4 py-2 rounded disabled:bg-gray-400">
                                Reject
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
