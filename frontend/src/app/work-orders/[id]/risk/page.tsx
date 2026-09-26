"use client";
import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";

export default function WorkOrderRiskDetail() {
  const params = useParams();
  const id = params.id as string;
  const [data, setData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [riskRes, histRes] = await Promise.all([
          fetch(`/api/v1/work-orders/${id}/risk`),
          fetch(`/api/v1/work-orders/${id}/risk/history`),
        ]);

        if (riskRes.status === 422) {
            throw new Error("Risk evaluation is currently unavailable because the plant timezone context is missing.");
        }
        if (!riskRes.ok) throw new Error("Failed to fetch risk details");

        const riskData = await riskRes.json();
        setData(riskData);

        if (histRes.ok) {
          const histData = await histRes.json();
          setHistory(histData || []);
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    if (id) fetchData();
  }, [id]);

  if (loading) return <div className="p-8">Loading...</div>;
  if (error) return <div className="p-8 text-red-500">{error}</div>;
  if (!data) return <div className="p-8">Not found</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Work Order: {data.order_number}</h1>
      <div className="bg-white p-6 shadow rounded-md mb-8">
        <h2 className="text-lg font-semibold border-b pb-2 mb-4">Risk State: {data.risk_state}</h2>
        <p className="text-gray-700 mb-4">{data.impact_summary}</p>
        <p className="text-sm text-gray-500">Status: {data.status}</p>
        <p className="text-sm text-gray-500">Due Date: {data.due_date || "N/A"}</p>
      </div>

      <h3 className="text-xl font-bold mb-4">Risk History</h3>
      {history.length === 0 ? (
        <p className="text-gray-500">No history available.</p>
      ) : (
        <div className="bg-white shadow rounded-md p-4">
          <ul className="divide-y">
            {history.map((h, i) => (
              <li key={i} className="py-2 text-sm">
                <span className="font-medium text-gray-900">{h.trigger_type}</span>:{" "}
                <span className="text-gray-600">{h.previous_state} → {h.new_state}</span>
                <span className="text-gray-400 ml-4">{new Date(h.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
