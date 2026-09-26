'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import {
  Users,
  Truck,
  Package,
  Settings2,
  ClipboardList,
  Upload,
  LayoutDashboard,
  Home,
  Settings,
  LogOut,
  Menu,
  X,
  Zap,
  Bell,
  Search,
  AlertTriangle
} from 'lucide-react';
import { AuthProvider, useAuth } from '@/components/providers/AuthProvider';
import { ReactQueryProvider } from '@/components/providers/ReactQueryProvider';

const navSections = [
  {
    title: 'Home',
    items: [
      { name: 'Home', href: '/', icon: Home },
    ]
  },
  {
    title: 'Intelligence',
    items: [
      { name: 'Overview', href: '/overview', icon: LayoutDashboard },
      { name: 'Command Center', href: '/command-center', icon: Zap },
      { name: 'Manufacturing Events', href: '/events', icon: Zap },
      { name: 'Incidents', href: '/incidents', icon: AlertTriangle },
      { name: 'Production Risk', href: '/risk', icon: AlertTriangle },
    ]
  },
  {
    title: 'Operations',
    items: [
      { name: 'Work Orders', href: '/work-orders', icon: ClipboardList },
      { name: 'Machines', href: '/machines', icon: Settings2 },
    ]
  },
  {
    title: 'Master Data',
    items: [
      { name: 'Customers', href: '/customers', icon: Users },
      { name: 'Vendors', href: '/vendors', icon: Truck },
      { name: 'Products', href: '/products', icon: Package },
      { name: 'Imports', href: '/imports', icon: Upload },
    ]
  },
  {
    title: 'Configuration',
    items: [
      { name: 'Settings', href: '/settings', icon: Settings },
    ]
  }
];

function DashboardContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#040814] text-slate-300 font-sans overflow-hidden selection:bg-[var(--color-x-cyan)]/30">
      {/* Dynamic Background matching Landing Page */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-teal-500/5 rounded-full blur-[100px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/5 rounded-full blur-[100px]"></div>
        <div className="absolute top-[40%] right-[20%] w-[30%] h-[30%] bg-cyan-500/5 rounded-full blur-[100px]"></div>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-[#020617]/80 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-[#080f23]/80 backdrop-blur-md border-r border-white/10 transform transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static lg:z-auto flex flex-col shadow-2xl lg:shadow-none
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="relative flex items-center justify-center mt-2 h-12 px-4 border-b border-white/10 shrink-0">
          <Link href="/" className="flex items-center justify-center">
            <Image
              src="/Xaiote(icon).png"
              alt="Xaiote"
              width={147}
              height={47}
              className="h-16 w-auto drop-shadow-lg"
              priority
            />
          </Link>
          <button
            className="absolute right-4 lg:hidden text-slate-400 hover:text-white transition-colors p-1"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-4 overflow-y-auto scrollbar-hide">
          {navSections.map((section) => (
            <div key={section.title}>
              {section.title !== 'Home' && (
                <p className="px-3 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  {section.title}
                </p>
              )}
              <div className="space-y-1">
                {section.items.map((link) => {
                  const isActive = pathname === link.href || (link.href !== '/overview' && pathname.startsWith(link.href + '/'));
                  
                  return (
                    <Link
                      key={link.name}
                      href={link.href}
                      onClick={() => setSidebarOpen(false)}
                      className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group ${
                        isActive
                          ? 'bg-slate-800/50 text-[var(--color-x-cyan)] border border-[var(--color-x-cyan)]/20 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                          : 'text-slate-400 hover:bg-slate-800/30 hover:text-white border border-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <link.icon className={`h-4 w-4 flex-shrink-0 transition-colors ${isActive ? 'text-[var(--color-x-cyan)]' : 'text-slate-500 group-hover:text-slate-300'}`} />
                        {link.name}
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* User Profile */}
        <div className="p-4 border-t border-white/10 bg-[#020617]/40">
          {loading ? (
            <div className="text-sm text-slate-500 animate-pulse pl-2">Loading profile...</div>
          ) : user ? (
            <div className="flex items-center justify-between bg-white/5 rounded-xl p-3 border border-white/5 backdrop-blur-sm">
              <div className="truncate pr-2">
                <div className="text-sm font-semibold text-white truncate">{user.full_name}</div>
                <div className="text-xs text-slate-400 truncate">{user.email}</div>
              </div>
              <button
                onClick={logout}
                className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/20 rounded-lg transition-colors border border-transparent hover:border-red-500/20"
                title="Sign Out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="block text-center py-2 text-sm text-[var(--color-x-cyan)] hover:text-cyan-300 font-medium rounded-lg bg-white/5 border border-white/5 transition-colors"
            >
              Sign In
            </Link>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 relative z-10">
        {/* Top Header */}
        <header className="h-[3.5rem] flex items-center justify-between px-4 lg:px-8 border-b border-white/10 bg-[#080f23]/60 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 -ml-2 text-slate-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
            >
              <Menu className="h-5 w-5" />
            </button>
            
            {/* Contextual Title */}
            <div className="hidden sm:flex items-center gap-2 text-sm font-medium">
               <span className="text-slate-500">Workspace</span>
               <span className="text-slate-700">/</span>
               <span className="text-slate-200 capitalize">{pathname.split('/')[1] || 'Overview'}</span>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Search */}
            <div className="hidden md:flex relative group">
               <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 group-focus-within:text-[var(--color-x-cyan)] transition-colors" />
               <input 
                 type="text" 
                 placeholder="Search intelligence..." 
                 className="bg-[#020617]/50 border border-white/10 rounded-full pl-9 pr-4 py-1.5 text-sm text-slate-300 focus:outline-none focus:border-[var(--color-x-cyan)]/50 focus:ring-1 focus:ring-[var(--color-x-cyan)]/50 transition-all placeholder:text-slate-600 w-64 shadow-inner"
               />
            </div>
            
            {/* Notifications */}
            <button className="relative p-2 text-slate-400 hover:text-white transition-colors rounded-full hover:bg-white/5 border border-transparent hover:border-white/10">
              <Bell className="h-5 w-5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[var(--color-x-cyan)] rounded-full border-2 border-[#080f23] animate-pulse"></span>
            </button>
          </div>
        </header>

        <main className="flex-1 p-4 lg:p-8 overflow-auto scrollbar-hide">
          {children}
        </main>
      </div>
    </div>
  );
}
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ReactQueryProvider>
      <AuthProvider>
        <DashboardContent>{children}</DashboardContent>
      </AuthProvider>
    </ReactQueryProvider>
  );
}
