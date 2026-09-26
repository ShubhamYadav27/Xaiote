import React from 'react';

const colorMap = {
    'NEEDS_REVIEW': 'bg-orange-100 text-orange-800 border-orange-300',
    'AMBIGUOUS': 'bg-yellow-100 text-yellow-800 border-yellow-300',
    'INSUFFICIENT_EVIDENCE': 'bg-gray-100 text-gray-800 border-gray-300',
    'FAILED': 'bg-red-100 text-red-800 border-red-300',
    'UNKNOWN': 'bg-slate-100 text-slate-800 border-slate-300',
    'ACCEPTED': 'bg-blue-100 text-blue-800 border-blue-300',
    'CONFIRMATION_TIMEOUT': 'bg-purple-100 text-purple-800 border-purple-300',
    'RECONCILIATION_REQUIRED': 'bg-red-200 text-red-900 border-red-400 font-bold'
};

export default function UncertaintyBadge({ status }: { status: string }) {
    const classes = (colorMap as any)[status] || 'bg-gray-100 text-gray-800';
    return (
        <span className={`px-2 py-1 text-xs border rounded-md uppercase ${classes}`}>
            {status}
        </span>
    );
}
