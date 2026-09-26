"use client";
import React, { useState, useEffect } from 'react';

export default function ExecutionsPage() {
    const [executions, setExecutions] = useState<any[]>([]);
    
    useEffect(() => {
        // Fetch running/accepted ExecutionAttempts
        fetch('/api/v1/executions?status=RUNNING,ACCEPTED')
            .then(res => res.json())
            .then(data => setExecutions(data.data || []));
    }, []);

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-4">Execution Tracking</h1>
            <div className="grid gap-4">
                {executions.length === 0 ? (
                    <p className="text-gray-500">No active external executions.</p>
                ) : executions.map((exec: any) => (
                    <div key={exec.id} className="border p-4 rounded shadow-sm bg-white">
                        <h3 className="font-semibold">Attempt: {exec.id}</h3>
                        <p className="text-sm text-gray-600">Status: <span className="font-mono bg-gray-100 px-1 rounded">{exec.status}</span></p>
                        <p className="text-sm text-gray-600">Action: {exec.action_instance_id}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}
