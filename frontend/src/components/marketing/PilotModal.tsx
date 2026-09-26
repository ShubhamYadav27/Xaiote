'use client';

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, ArrowRight, Loader2 } from 'lucide-react';
import { fetchApi } from '@/lib/api';

export const OPEN_PILOT_MODAL_EVENT = 'xaiote:open-pilot-modal';

export function openPilotModal(e?: React.MouseEvent) {
  if (e) e.preventDefault();
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(OPEN_PILOT_MODAL_EVENT));
  }
}

export function PilotModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
    const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    const formData = new FormData(e.currentTarget);
    const payload = {
      full_name: formData.get('full_name'),
      email: formData.get('email'),
      company_name: formData.get('company'),
      team_size: formData.get('team-size'),
      role: formData.get('role'),
      primary_challenge: formData.get('challenge'),
    };

    try {
      await fetchApi('/company/pilot', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Failed to submit request');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setMounted(true);
    const handleOpen = () => setIsOpen(true);
    window.addEventListener(OPEN_PILOT_MODAL_EVENT, handleOpen);
    return () => window.removeEventListener(OPEN_PILOT_MODAL_EVENT, handleOpen);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) setIsOpen(false);
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  if (!isOpen || !mounted) return null;

  return createPortal(
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pilot-modal-title"
    >
      <div 
        className="absolute inset-0 bg-[#020617]/80 backdrop-blur-xl transition-opacity duration-300" 
        onClick={() => setIsOpen(false)}
      ></div>
      
      <div className="relative w-full max-w-lg bg-[#080f23] border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-300">
        <div className="flex justify-between items-start p-6 pb-2">
          <div>
            <h2 id="pilot-modal-title" className="text-xl font-bold text-white mb-2">Book a Pilot</h2>
            <p className="text-sm text-slate-400">See how Xaiote connects your operational data and surfaces production risk.</p>
          </div>
          <button 
            onClick={() => setIsOpen(false)} 
            className="text-slate-400 hover:text-white transition-colors p-1 -mr-2"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 pt-4">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="full-name" className="block text-sm font-medium text-slate-300 mb-1.5">Full name</label>
              <input required type="text" id="full-name" name="full_name" className="w-full px-4 py-2.5 bg-slate-900/50 border border-white/10 text-white rounded-lg focus:ring-1 focus:ring-[var(--color-x-teal)] focus:border-[var(--color-x-teal)] outline-none transition-all placeholder-slate-600" placeholder="Jane Smith" />
            </div>
            
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1.5">Work email</label>
              <input required type="email" id="email" name="email" className="w-full px-4 py-2.5 bg-slate-900/50 border border-white/10 text-white rounded-lg focus:ring-1 focus:ring-[var(--color-x-teal)] focus:border-[var(--color-x-teal)] outline-none transition-all placeholder-slate-600" placeholder="jane@company.com" />
            </div>
            
            <div>
              <label htmlFor="company" className="block text-sm font-medium text-slate-300 mb-1.5">Company</label>
              <input required type="text" id="company" name="company" className="w-full px-4 py-2.5 bg-slate-900/50 border border-white/10 text-white rounded-lg focus:ring-1 focus:ring-[var(--color-x-teal)] focus:border-[var(--color-x-teal)] outline-none transition-all placeholder-slate-600" placeholder="Acme Inc." />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="team-size" className="block text-sm font-medium text-slate-300 mb-1.5">Team size</label>
                <select id="team-size" name="team-size" className="w-full px-4 py-2.5 bg-slate-900/50 border border-white/10 text-slate-300 rounded-lg focus:ring-1 focus:ring-[var(--color-x-teal)] focus:border-[var(--color-x-teal)] outline-none transition-all appearance-none">
                  <option>Select</option>
                  <option>1-50</option>
                  <option>51-200</option>
                  <option>201-1000</option>
                  <option>1000+</option>
                </select>
              </div>
              <div>
                <label htmlFor="role" className="block text-sm font-medium text-slate-300 mb-1.5">Your role</label>
                <select id="role" name="role" className="w-full px-4 py-2.5 bg-slate-900/50 border border-white/10 text-slate-300 rounded-lg focus:ring-1 focus:ring-[var(--color-x-teal)] focus:border-[var(--color-x-teal)] outline-none transition-all appearance-none">
                  <option>Select</option>
                  <option>Owner / MD</option>
                  <option>Plant Head</option>
                  <option>CTO / IT Leadership</option>
                  <option>Production Management</option>
                  <option>Other</option>
                </select>
              </div>
            </div>
            
            
            <div>
              <label htmlFor="challenge" className="block text-sm font-medium text-slate-300 mb-1.5">Primary production challenge</label>
              <textarea id="challenge" name="challenge" rows={3} className="w-full px-4 py-2.5 bg-slate-900/50 border border-white/10 text-white rounded-lg focus:ring-1 focus:ring-[var(--color-x-teal)] focus:border-[var(--color-x-teal)] outline-none transition-all placeholder-slate-600 resize-y" placeholder="Tell us about your primary production challenge"></textarea>
            </div>
            
            <div className="pt-2">
              <button 
                type="submit" 
                className="w-full bg-[var(--color-x-teal)] hover:bg-teal-500 text-white font-bold py-3 px-4 rounded-lg shadow-lg transition-all flex items-center justify-center gap-2"
              >
                Request Pilot
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>,
    document.body
  );
}
