"use client";
import Link from "next/link";
import Image from "next/image";
import { Menu, X, ArrowRight } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import { openPilotModal } from "@/components/marketing/PilotModal";

export function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const { user, loading } = useAuth();

  const links = [
    { name: "Product", href: "/product" },
    { name: "How It Works", href: "/how-it-works" },
    { name: "Solutions", href: "/solutions" },
    { name: "Industries", href: "/industries" },
    { name: "Security", href: "/security" },
    { name: "Resources", href: "/resources" },
    { name: "Company", href: "/company" },
  ];

  return (
    <nav className="fixed top-0 w-full z-50 bg-slate-950/80 backdrop-blur-md border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center">
            <Link href="/" className="flex items-center">
              <Image src="/Logo(icon).png" alt="Xaiote" width={120} height={52} className="h-15 w-auto" priority />
            </Link>
          </div>
          
          <div className="hidden md:flex items-center space-x-6 text-sm font-semibold">
            {links.map((link) => (
              <Link key={link.name} href={link.href} className="text-slate-300 hover:text-white transition-colors">
                {link.name}
              </Link>
            ))}
          </div>

          <div className="hidden md:flex items-center space-x-4">
            {loading ? (
              <div className="w-[71px] h-[34px] border border-transparent"></div>
            ) : user ? (
              <Link 
                href="/overview" 
                className="text-sm font-semibold text-white bg-transparent border border-white/20 rounded-lg px-3.5 py-1.5 hover:bg-slate-800 transition-colors"
              >
                Dashboard
              </Link>
            ) : (
              <Link 
                href="/login" 
                className="text-sm font-semibold text-white bg-transparent border border-white/20 rounded-lg px-3.5 py-1.5 hover:bg-slate-800 transition-colors"
              >
                Sign In
              </Link>
            )}
            <button onClick={openPilotModal} className="bg-[var(--color-x-teal)] hover:bg-teal-500 text-white px-4 py-2 rounded-md text-sm font-semibold transition-colors flex items-center gap-2 shadow-lg">Book a Pilot<ArrowRight className="w-4 h-4" /></button>
          </div>

          <div className="md:hidden flex items-center">
            <button onClick={() => setIsOpen(!isOpen)} className="text-slate-300 hover:text-white">
              {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {isOpen && (
        <div className="md:hidden bg-slate-950 border-b border-white/10 px-4 pt-2 pb-4 space-y-1 shadow-lg">
          {links.map((link) => (
            <Link 
              key={link.name} 
              href={link.href} 
              className="block px-3 py-2 rounded-md text-base font-semibold text-slate-300 hover:text-white hover:bg-slate-900"
              onClick={() => setIsOpen(false)}
            >
              {link.name}
            </Link>
          ))}
          <div className="pt-4 mt-4 border-t border-slate-800 flex flex-col gap-3 px-3">
                        {loading ? (
              <div className="h-[42px] border border-transparent"></div>
            ) : user ? (
              <Link href="/overview" className="text-base font-semibold text-white border border-white/20 rounded-lg px-4 py-2 text-center hover:bg-slate-800 transition-colors">Dashboard</Link>
            ) : (
              <Link href="/login" className="text-base font-semibold text-white border border-white/20 rounded-lg px-4 py-2 text-center hover:bg-slate-800 transition-colors">Sign In</Link>
            )}
            <button onClick={(e) => { setIsOpen(false); openPilotModal(e); }} className="text-base font-semibold text-white bg-[var(--color-x-teal)] hover:bg-teal-500 transition-colors px-4 py-2 rounded-lg text-center shadow-lg w-full">Book a Pilot</button>
          </div>
        </div>
      )}
    </nav>
  );
}
