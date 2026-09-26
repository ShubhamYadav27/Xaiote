import Link from "next/link";
import { openPilotModal } from "@/components/marketing/PilotModal";
import { ArrowRight, ArrowDown, Activity, ShieldCheck, FileText, Database } from "lucide-react";

export function RoadmapArchitecture() {
  return (
    <section className="py-24 bg-transparent border-t border-white/10 overflow-hidden relative">
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-20">
          <span className="inline-block px-3 py-1 bg-slate-900 border border-slate-800 text-slate-400 rounded-full text-xs font-bold uppercase tracking-widest mb-4">Vision & Roadmap</span>
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">From Production Visibility to a Manufacturing Intelligence OS.</h2>
          <p className="text-lg text-slate-400">
            Xaiote's current foundation is deterministic risk detection. The future is an autonomous operational nervous system for the factory floor.
          </p>
        </div>
        
        <div className="max-w-4xl mx-auto">
          {/* Current MVP vs Roadmap Boundary */}
          <div className="relative border-2 border-white/10 rounded-3xl p-8 bg-transparent shadow-sm mb-8 z-10">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-transparent px-4">
              <span className="text-xs font-bold text-[var(--color-x-teal)] tracking-widest uppercase">Current Platform</span>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-64 text-center bg-slate-900 text-white font-bold text-xl py-4 rounded-xl shadow-lg border border-slate-800 mb-8">
                XAIOTE
              </div>
              
              <div className="flex justify-center gap-4 md:gap-16 relative w-full mb-8">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[60%] md:w-[70%] h-px bg-slate-700"></div>
                
                <div className="flex flex-col items-center pt-8 relative w-1/3">
                  <div className="absolute top-0 left-1/2 w-px h-8 bg-slate-700 -translate-x-1/2"></div>
                  <Activity className="w-8 h-8 text-[var(--color-x-cyan)] mb-3" />
                  <span className="font-bold text-white text-center">Production<br/>Intelligence</span>
                </div>
                <div className="flex flex-col items-center pt-8 relative w-1/3">
                  <div className="absolute top-0 left-1/2 w-px h-8 bg-slate-700 -translate-x-1/2"></div>
                  <ShieldCheck className="w-8 h-8 text-[var(--color-x-amber)] mb-3" />
                  <span className="font-bold text-white text-center">Risk<br/>Intelligence</span>
                </div>
                <div className="flex flex-col items-center pt-8 relative w-1/3">
                  <div className="absolute top-0 left-1/2 w-px h-8 bg-slate-700 -translate-x-1/2"></div>
                  <FileText className="w-8 h-8 text-[var(--color-x-teal)] mb-3" />
                  <span className="font-bold text-white text-center">Evidence<br/>Intelligence</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col items-center">
            <ArrowDown className="w-6 h-6 text-slate-400 mb-4" />
            
            <div className="relative w-full max-w-2xl">
              {/* Boundary line */}
              <div className="absolute top-1/2 left-0 w-full border-t border-dashed border-slate-700 -z-10"></div>
              
              <div className="bg-slate-900/50 border border-white/10 border-dashed rounded-3xl p-8 text-center relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[var(--color-x-blue)]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <Database className="w-10 h-10 text-slate-400 mx-auto mb-4" />
                <h3 className="text-2xl font-bold text-white uppercase tracking-widest mb-2 group-hover:text-[var(--color-x-blue)] transition-colors">Manufacturing Intelligence OS</h3>
                <p className="text-sm text-slate-400 font-medium">Predictive Maintenance • Machine Control • Delay Prediction • Recovery Recommendations • Direct ERP/IoT APIs</p>
              </div>
            </div>
          </div>
          
        </div>
      </div>
    </section>
  );
}

export function PilotCTA() {
  return (
    <section className="py-32 bg-transparent border-t border-white/5 relative overflow-hidden">
      {/* <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-5"></div> */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-6">
          Know what needs attention before the delivery date does.
        </h2>
        <p className="text-xl text-slate-400 mb-10">
          Connect your production data and shop-floor signals. Turn fragmented operational information into evidence-backed production intelligence.
        </p>
        <div className="flex flex-col sm:flex-row justify-center gap-4">
          <button onClick={openPilotModal} className="inline-flex justify-center items-center gap-2 bg-[var(--color-x-teal)] hover:bg-teal-500 text-white shadow-lg px-8 py-4 rounded-md font-bold text-lg transition-colors w-full sm:w-auto">Book a Pilot<ArrowRight className="w-5 h-5" /></button>
          <Link href="/contact" className="inline-flex justify-center items-center gap-2 bg-transparent hover:bg-slate-900 border border-slate-700 text-white px-8 py-4 rounded-md font-bold text-lg transition-colors">
            Talk to Xaiote
          </Link>
        </div>
      </div>
    </section>
  );
}
