'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { register, login, isAuthenticated } from '@/lib/auth';
import { useEffect } from 'react';

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    company_name: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace('/customers');
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await register(formData);
      // Auto-login after registration
      await login({ email: formData.email, password: formData.password });
      router.push('/customers');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const update = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8 flex flex-col items-center">
          <Link href="/" className="inline-flex flex-col items-center group">
            <Image
              src="/Logo(icon).png"
              alt="Xaiote Icon"
              width={48}
              height={48}
              className="h-12 w-auto mb-3 transition-transform duration-300 group-hover:scale-105"
              priority
            />
            <Image
              src="/Xaiote(icon).png"
              alt="Xaiote"
              width={120}
              height={28}
              className="h-15 w-auto mb-6"
              priority
            />
          </Link>
          <h1 className="text-2xl font-bold text-white">Create Your Account</h1>
          <p className="text-slate-400 mt-2">Start your manufacturing intelligence journey</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-slate-300 mb-1.5">
                Full Name
              </label>
              <input
                id="full_name"
                type="text"
                required
                value={formData.full_name}
                onChange={(e) => update('full_name', e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                placeholder="Your full name"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1.5">
                Work Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={formData.email}
                onChange={(e) => update('email', e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                placeholder="you@company.com"
                autoComplete="email"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={6}
                value={formData.password}
                onChange={(e) => update('password', e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                placeholder="Min. 6 characters"
                autoComplete="new-password"
              />
            </div>

            <div>
              <label htmlFor="company_name" className="block text-sm font-medium text-slate-300 mb-1.5">
                Company Name
              </label>
              <input
                id="company_name"
                type="text"
                required
                value={formData.company_name}
                onChange={(e) => update('company_name', e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                placeholder="Your manufacturing company"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-[var(--color-x-teal)] hover:bg-teal-500 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-slate-400">
            Already have an account?{' '}
            <Link href="/login" className="text-[var(--color-x-teal)] hover:text-teal-400 font-medium">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
