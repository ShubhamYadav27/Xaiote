'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { fetchApiUpload } from '@/lib/api';

export default function ImportsPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [importType, setImportType] = useState('CUSTOMERS');
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('import_type', importType);

      const data = await fetchApiUpload('/imports/upload', formData);
      router.push('/imports/' + data.id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <h1 className='text-2xl font-bold mb-6'>Imports</h1>
      
      <div className='bg-[#080f23]/50 backdrop-blur-md p-6 rounded border shadow-sm mb-8 max-w-lg'>
        <h2 className='text-lg font-bold mb-4'>Upload New Import</h2>
        <form onSubmit={handleUpload} className='space-y-4'>
          {error && <div className='bg-red-500/10 text-red-400 p-2 rounded text-sm'>{error}</div>}
          <div>
            <label className='block text-sm font-medium mb-1'>Entity Type</label>
            <select value={importType} onChange={e => setImportType(e.target.value)} className='w-full bg-[#020617]/50 border border-white/10 p-2 rounded text-slate-200 focus:outline-none focus:border-[var(--color-x-cyan)]/50'>
              <option value='CUSTOMERS'>Customer</option>
              <option value='VENDORS'>Vendor</option>
              <option value='PRODUCTS'>Product</option>
              <option value='MACHINES'>Machine</option>
            </select>
          </div>
          <div>
            <label className='block text-sm font-medium mb-1'>CSV File</label>
            <input type='file' accept='.csv' onChange={e => setFile(e.target.files?.[0] || null)} className='w-full bg-[#020617]/50 border border-white/10 p-2 rounded text-slate-200 focus:outline-none focus:border-[var(--color-x-cyan)]/50' required />
          </div>
          <button type='submit' disabled={!file || uploading} className='px-4 py-2 bg-[var(--color-x-cyan)]/20 border border-[var(--color-x-cyan)]/50 text-[var(--color-x-cyan)] rounded hover:bg-[var(--color-x-cyan)]/40 disabled:opacity-50'>
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </form>
      </div>
    </div>
  );
}
