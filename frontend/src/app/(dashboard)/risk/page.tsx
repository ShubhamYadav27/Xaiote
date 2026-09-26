"use client";

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api';

export default function ProductionRiskPage() {
    const [items, setItems] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchApi('/risk/dashboard').then(data => {
            setItems(Array.isArray(data) ? data : data.items || data.data || []);
            setLoading(false);
        }).catch(() => setLoading(false));
    }, []);

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-6">Production Risk Dashboard</h1>
            {loading ? <p>Loading...</p> : (
                <div className="grid gap-4">
                    {items.length === 0 ? <p className="text-gray-500">No risk records found.</p> : 
                    items.map((item: any, idx: number) => (
                        <div key={idx} className="border p-4 rounded-md shadow-sm bg-white">
                            <h3 className="font-semibold text-lg">{item.work_order_id}</h3>
                            <p>State: <span className="font-mono bg-gray-100 px-2 py-1 rounded text-sm">{item.state}</span></p>
                            <p>Due: {item.due_date}</p>
                            {item.impacts && item.impacts.length > 0 && (
                                <div className="mt-2 text-sm text-red-600 border-t pt-2">
                                    Impacts: {item.impacts.length}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
