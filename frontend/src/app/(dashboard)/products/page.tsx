'use client';
import { useState, useEffect } from 'react';
import { fetchApi } from '@/lib/api';
import { Modal } from '@/components/Modal';

export default function ProductsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({ name: '', external_id: '', sku: '' });
  const [formError, setFormError] = useState<string | null>(null);

  const limit = 10;

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchApi('/products?limit=' + limit + '&offset=' + ((page - 1) * limit));
      setItems(data.items);
      setTotal(data.total);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      await fetchApi('/products', {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      setIsModalOpen(false);
      setFormData({ name: '', external_id: '', sku: '' });
      loadData();
    } catch (e: any) {
      setFormError(e.message);
    }
  };

  return (
    <div>
      <div className='flex justify-between items-center mb-6'>
        <h1 className='text-2xl font-bold text-white tracking-tight'>Products</h1>
        <button onClick={() => setIsModalOpen(true)} className='bg-[var(--color-x-cyan)]/20 border border-[var(--color-x-cyan)]/50 text-[var(--color-x-cyan)] px-4 py-2 rounded hover:bg-[var(--color-x-cyan)]/40'>
          Add Product
        </button>
      </div>

      {error && <div className='bg-red-500/10 text-red-400 p-4 rounded mb-4'>{error}</div>}

      {loading ? (
        <div className='text-slate-500'>Loading...</div>
      ) : items.length === 0 ? (
        <div className='text-slate-500 bg-[#080f23]/50 backdrop-blur-md p-8 rounded border text-center'>No products found.</div>
      ) : (
        <div className='bg-[#080f23]/50 backdrop-blur-md border rounded overflow-hidden'>
          <table className='w-full text-left'>
            <thead className='bg-white/5 border-b'>
              <tr>
                <th className='p-3'>ID</th>
                <th className='p-3'>Product Name</th>
                <th className='p-3'>External ID</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={item.id} className='border-b last:border-0'>
                  <td className='p-3'>{item.id}</td>
                  <td className='p-3'>{item.name}</td>
                  <td className='p-3'>{item.external_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className='p-3 border-t flex justify-between items-center bg-white/5'>
            <span className='text-sm text-slate-400'>Showing {items.length} of {total}</span>
            <div className='space-x-2'>
              <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className='px-3 py-1 border border-white/10 rounded hover:bg-white/5 disabled:opacity-50'>Previous</button>
              <button disabled={page * limit >= total} onClick={() => setPage(p => p + 1)} className='px-3 py-1 border border-white/10 rounded hover:bg-white/5 disabled:opacity-50'>Next</button>
            </div>
          </div>
        </div>
      )}

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title='Add Product'>
        <form onSubmit={handleSubmit} className='space-y-4'>
          {formError && <div className='bg-red-500/10 text-red-400 p-2 rounded text-sm'>{formError}</div>}
          <div>
            <label className='block text-sm font-medium mb-1'>Name</label>
            <input required type='text' value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className='w-full bg-[#020617]/50 border border-white/10 p-2 rounded text-slate-200 focus:outline-none focus:border-[var(--color-x-cyan)]/50' />
          </div>
          <div>
            <label className='block text-sm font-medium mb-1'>SKU (Optional)</label>
            <input type='text' value={formData.sku} onChange={e => setFormData({...formData, sku: e.target.value})} className='w-full bg-[#020617]/50 border border-white/10 p-2 rounded text-slate-200 focus:outline-none focus:border-[var(--color-x-cyan)]/50' placeholder='e.g. PROD-001' />
          </div>
          <div>
            <label className='block text-sm font-medium mb-1'>External ID (Optional)</label>
            <input type='text' value={formData.external_id} onChange={e => setFormData({...formData, external_id: e.target.value})} className='w-full bg-[#020617]/50 border border-white/10 p-2 rounded text-slate-200 focus:outline-none focus:border-[var(--color-x-cyan)]/50' />
          </div>
          <div className='flex justify-end space-x-2 pt-4'>
            <button type='button' onClick={() => setIsModalOpen(false)} className='px-4 py-2 border border-white/10 rounded text-slate-300 hover:bg-white/5'>Cancel</button>
            <button type='submit' className='px-4 py-2 bg-[var(--color-x-cyan)]/20 border border-[var(--color-x-cyan)]/50 text-[var(--color-x-cyan)] rounded hover:bg-[var(--color-x-cyan)]/40'>Save</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
