"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, CheckCircle, Clock, AlertTriangle } from "lucide-react";

type RiskState =
  | "RESOLVED"
  | "NOT_APPLICABLE"
  | "ON_TRACK"
  | "PENDING_EVALUATION"
  | "AT_RISK"
  | "DELAYED"
  | "CRITICAL";

interface RiskItem {
  work_order_id: string;
  order_number: string;
  plant_id: string;
  customer_id: string | null;
  due_date: string | null;
  status: string;
  risk_state: RiskState;
  impact_summary: string;
  last_evaluated_at: string | null;
}

export default function RiskDashboard() {
  const [items, setItems] = useState<RiskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/v1/risk/dashboard");
        if (!res.ok) {
          throw new Error("Failed to fetch risk data");
        }
        const data = await res.json();
        setItems(data.items || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const getRiskIcon = (state: RiskState) => {
    switch (state) {
      case "CRITICAL":
      case "AT_RISK":
        return <AlertTriangle className="w-5 h-5 text-red-500" />;
      case "DELAYED":
      case "PENDING_EVALUATION":
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      case "ON_TRACK":
      case "RESOLVED":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  if (loading) return <div className="p-8">Loading risk dashboard...</div>;
  if (error) return <div className="p-8 text-red-500">Error: {error}</div>;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Work Order Risk Dashboard</h1>
      {items.length === 0 ? (
        <div className="text-gray-500">No active work orders with risk tracking found.</div>
      ) : (
        <div className="bg-white shadow overflow-hidden rounded-md">
          <ul className="divide-y divide-gray-200">
            {items.map((item) => (
              <li key={item.work_order_id}>
                <Link href={`/work-orders/${item.work_order_id}/risk`} className="block hover:bg-gray-50 px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col">
                      <p className="text-sm font-medium text-blue-600 truncate">{item.order_number}</p>
                      <p className="text-sm text-gray-500 mt-1">Status: {item.status}</p>
                    </div>
                    <div className="flex flex-col items-end">
                      <div className="flex items-center gap-2">
                        {getRiskIcon(item.risk_state)}
                        <span className="text-sm font-medium text-gray-900">{item.risk_state}</span>
                      </div>
                      <p className="text-sm text-gray-500 mt-1 truncate max-w-md" title={item.impact_summary}>
                        {item.impact_summary}
                      </p>
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
