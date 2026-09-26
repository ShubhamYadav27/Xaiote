import codecs

file_path = 'src/components/marketing/PilotModal.tsx'
with codecs.open(file_path, 'r', 'utf-8') as f:
    content = f.read()

import_replacement = '''import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, ArrowRight, Loader2 } from 'lucide-react';
import { fetchApi } from '@/lib/api';'''
content = content.replace("import { X, ArrowRight } from 'lucide-react';", import_replacement)

# Add state for form
state_replacement = '''  const [isOpen, setIsOpen] = useState(false);
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
  };'''
content = content.replace("  const [mounted, setMounted] = useState(false);", state_replacement)

# Update form tag
content = content.replace('<form className="space-y-4">', '<form className="space-y-4" onSubmit={handleSubmit}>')

# Add name attributes to inputs
content = content.replace('id="full-name"', 'id="full-name" name="full_name"')
content = content.replace('id="email"', 'id="email" name="email"')
content = content.replace('id="company"', 'id="company" name="company"')
content = content.replace('id="team-size"', 'id="team-size" name="team-size"')
content = content.replace('id="role"', 'id="role" name="role"')
content = content.replace('id="challenge"', 'id="challenge" name="challenge"')

# Replace form content with success state if success
form_content_replacement = '''        <div className="p-6 pt-4">
          {success ? (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-teal-500/20 text-teal-400 rounded-full flex items-center justify-center mx-auto mb-4">
                <ArrowRight className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Request Received</h3>
              <p className="text-slate-400 mb-6">Thank you for your interest in Xaiote. Our team will reach out to you shortly to schedule your pilot evaluation.</p>
              <button onClick={() => setIsOpen(false)} className="w-full bg-slate-800 hover:bg-slate-700 text-white font-bold py-3 px-4 rounded-lg transition-all">Close</button>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={handleSubmit}>
              {error && <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">{error}</div>}'''
content = content.replace('        <div className="p-6 pt-4">\n          <form className="space-y-4" onSubmit={handleSubmit}>', form_content_replacement)
content = content.replace('          <form className="space-y-4">', '<form className="space-y-4" onSubmit={handleSubmit}>')

# Update submit button
button_replacement = '''            <div className="pt-2">
              <button 
                type="submit" 
                disabled={loading}
                className="w-full bg-[var(--color-x-teal)] hover:bg-teal-500 disabled:opacity-50 text-white font-bold py-3 px-4 rounded-lg shadow-lg transition-all flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Request Pilot'}
                {!loading && <ArrowRight className="w-4 h-4" />}
              </button>
            </div>
          </form>
          )}
        </div>'''
content = content.replace('''            <div className="pt-2">
              <button 
                type="submit" 
                className="w-full bg-[var(--color-x-teal)] hover:bg-teal-500 text-white font-bold py-3 px-4 rounded-lg shadow-lg transition-all flex items-center justify-center gap-2"
              >
                Request Pilot
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>''', button_replacement)

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(content)
