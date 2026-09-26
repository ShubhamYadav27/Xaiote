'use client';
import { useState, useEffect } from 'react';
import { fetchApi } from '@/lib/api';
import { useParams } from 'next/navigation';

export default function ImportJobPage() {
  const { id } = useParams();
  const [job, setJob] = useState<any>(null);
  const [audits, setAudits] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const limit = 10;

  useEffect(() => {
    const loadData = async () => {
      try {
        const jobData = await fetchApi('/imports/' + id);
        setJob(jobData);
        
        const auditData = await fetchApi('/imports/' + id + '/audits?limit=' + limit + '&offset=' + ((page - 1) * limit));
        setAudits(auditData.items);
        setTotal(auditData.total);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [id, page]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div className='bg-red-500/10 text-red-400 p-4 rounded'>{error}</div>;

  return (
    <div>
      <h1 className='text-2xl font-bold mb-6'>Import Job Status</h1>
      
      {job && (
        <div className='bg-[#080f23]/50 backdrop-blur-md p-6 rounded border shadow-sm mb-8 grid grid-cols-2 gap-4'>
          <div><strong>Status:</strong> {job.status}</div>
          <div><strong>Type:</strong> {job.import_type}</div>
          <div><strong>Filename:</strong> {job.source_filename}</div>
          <div><strong>Total Rows:</strong> {job.total_rows}</div>
          <div><strong>Valid Rows:</strong> {job.valid_rows}</div>
          <div><strong>Invalid Rows:</strong> {job.invalid_rows}</div>
          <div><strong>Needs Review:</strong> {job.needs_review_rows}</div>
          <div><strong>Created:</strong> {job.created_rows}</div>
          <div><strong>Updated:</strong> {job.updated_rows}</div>
          <div><strong>Unchanged:</strong> {job.unchanged_rows}</div>
        </div>
      )}

      <h2 className='text-lg font-bold mb-4'>Audit Logs</h2>
      {audits.length === 0 ? (
        <div className='text-slate-500 bg-[#080f23]/50 backdrop-blur-md p-8 rounded border text-center'>No audit logs.</div>
      ) : (
        <div className='bg-[#080f23]/50 backdrop-blur-md border rounded overflow-hidden'>
          <table className='w-full text-left text-sm'>
            <thead className='bg-white/5 border-b'>
              <tr>
                <th className='p-3'>Row</th>
                <th className='p-3'>Status</th>
                <th className='p-3'>Operation</th>
                <th className='p-3'>Error Msg</th>
                <th className='p-3'>Raw Data</th>
              </tr>
            </thead>
            <tbody>
              {audits.map(a => (
                <tr key={a.id} className='border-b last:border-0'>
                  <td className='p-3'>{a.source_row_number}</td>
                  <td className='p-3'>{a.status}</td>
                  <td className='p-3'>{a.operation}</td>
                  <td className='p-3 text-red-600'>{a.error_message}</td>
                  <td className='p-3 truncate max-w-xs'>{JSON.stringify(a.raw_data)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className='p-3 border-t flex justify-between items-center bg-white/5'>
            <span className='text-sm text-slate-400'>Showing {audits.length} of {total}</span>
            <div className='space-x-2'>
              <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className='px-3 py-1 border border-white/10 rounded hover:bg-white/5 disabled:opacity-50'>Previous</button>
              <button disabled={page * limit >= total} onClick={() => setPage(p => p + 1)} className='px-3 py-1 border border-white/10 rounded hover:bg-white/5 disabled:opacity-50'>Next</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
