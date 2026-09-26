'use client';

import { useAuth } from '@/components/providers/AuthProvider';
import { User, Building2, Bell, Link2, Shield, Database, LogOut } from 'lucide-react';

export default function SettingsPage() {
  const { user, logout } = useAuth();

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-slate-400 mt-1">Manage your account, workspace, and platform preferences.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-2">
          <h2 className="text-sm font-semibold text-white">Account</h2>
          <p className="text-sm text-slate-400">Your personal profile information.</p>
        </div>
        <div className="lg:col-span-2 bg-[#080f23]/50 backdrop-blur-md border border-white/10 rounded-xl p-6 shadow-xl">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center border border-white/10">
              <User className="w-6 h-6 text-slate-300" />
            </div>
            <div>
              <div className="font-semibold text-white">{user?.full_name || 'Loading...'}</div>
              <div className="text-sm text-slate-400">{user?.email || 'Loading...'}</div>
            </div>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Full Name</label>
              <div className="text-sm text-slate-200 bg-slate-900/50 border border-white/5 rounded-lg px-3 py-2">
                {user?.full_name || '---'}
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Email Address</label>
              <div className="text-sm text-slate-200 bg-slate-900/50 border border-white/5 rounded-lg px-3 py-2">
                {user?.email || '---'}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="w-full h-px bg-white/5 my-8"></div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-2">
          <h2 className="text-sm font-semibold text-white">Workspace</h2>
          <p className="text-sm text-slate-400">Organization and team settings.</p>
        </div>
        <div className="lg:col-span-2 bg-[#080f23]/50 backdrop-blur-md border border-white/10 rounded-xl p-6 shadow-xl">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center border border-white/10 mt-1">
              <Building2 className="w-5 h-5 text-slate-300" />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Organization ID</label>
              <div className="text-sm text-slate-200 bg-slate-900/50 border border-white/5 rounded-lg px-3 py-2 mb-4">
                {user?.company_id || '---'}
              </div>
              <p className="text-xs text-slate-500">Contact enterprise support to modify workspace ownership or limits.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="w-full h-px bg-white/5 my-8"></div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 opacity-60">
        <div className="lg:col-span-1 space-y-2">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">Preferences <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-800 border border-white/10">Coming Soon</span></h2>
          <p className="text-sm text-slate-400">Dashboard UI and notification alerts.</p>
        </div>
        <div className="lg:col-span-2 bg-[#080f23]/30 backdrop-blur-sm border border-white/5 rounded-xl p-6 shadow-lg">
          <div className="flex items-center gap-3 text-slate-400">
            <Bell className="w-5 h-5" />
            <span className="text-sm">Notification preferences are currently managed via account manager.</span>
          </div>
        </div>
      </div>

      <div className="w-full h-px bg-white/5 my-8"></div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 opacity-60">
        <div className="lg:col-span-1 space-y-2">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">Integrations <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-800 border border-white/10">Coming Soon</span></h2>
          <p className="text-sm text-slate-400">Connect ERP and MES systems.</p>
        </div>
        <div className="lg:col-span-2 bg-[#080f23]/30 backdrop-blur-sm border border-white/5 rounded-xl p-6 shadow-lg">
          <div className="flex items-center gap-3 text-slate-400">
            <Link2 className="w-5 h-5" />
            <span className="text-sm">Self-service integration portal will be available in the next release.</span>
          </div>
        </div>
      </div>

      <div className="w-full h-px bg-white/5 my-8"></div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 opacity-60">
        <div className="lg:col-span-1 space-y-2">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">Security <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-800 border border-white/10">Coming Soon</span></h2>
          <p className="text-sm text-slate-400">Password and session management.</p>
        </div>
        <div className="lg:col-span-2 bg-[#080f23]/30 backdrop-blur-sm border border-white/5 rounded-xl p-6 shadow-lg">
          <div className="flex items-center gap-3 text-slate-400">
            <Shield className="w-5 h-5" />
            <span className="text-sm">Security settings are inherited from your organizational SSO.</span>
          </div>
        </div>
      </div>

      <div className="w-full h-px bg-white/5 my-8"></div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 opacity-60">
        <div className="lg:col-span-1 space-y-2">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">Data & Imports <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-800 border border-white/10">Coming Soon</span></h2>
          <p className="text-sm text-slate-400">Data retention and bulk operations.</p>
        </div>
        <div className="lg:col-span-2 bg-[#080f23]/30 backdrop-blur-sm border border-white/5 rounded-xl p-6 shadow-lg">
          <div className="flex items-center gap-3 text-slate-400">
            <Database className="w-5 h-5" />
            <span className="text-sm">Manage active imports directly from the Master Data sidebar.</span>
          </div>
        </div>
      </div>

      <div className="w-full h-px bg-white/5 my-8"></div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-2">
          <h2 className="text-sm font-semibold text-white">Sign Out</h2>
          <p className="text-sm text-slate-400">End your current session.</p>
        </div>
        <div className="lg:col-span-2 bg-[#080f23]/50 backdrop-blur-md border border-white/10 rounded-xl p-6 shadow-xl flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-white">Log out of Xaiote</div>
            <div className="text-xs text-slate-400 mt-1">You will be securely signed out of this browser.</div>
          </div>
          <button 
            onClick={logout}
            className="flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 px-4 py-2 rounded-lg text-sm font-semibold transition-colors border border-red-500/20"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
