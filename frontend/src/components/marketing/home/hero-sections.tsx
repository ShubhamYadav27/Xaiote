import Link from "next/link";
import { openPilotModal } from "@/components/marketing/PilotModal";
import Image from "next/image";
import { ArrowRight, CheckCircle2, XCircle } from "lucide-react";

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-24 pb-32 bg-slate-900">
      {/* Background Image Layer */}
      <div 
        className="absolute inset-0 z-0 pointer-events-none"
        style={{
          backgroundImage: "url('/Background.png')",
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat"
        }}
      />
      
      {/* Existing Grid Pattern */}
      {/* <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-10 z-[1] pointer-events-none"></div> */}
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div className="max-w-xl relative z-10 lg:pr-8">
            <div className="mb-6 relative z-10">
              <Image src="/Xaiote(icon).png" alt="Xaiote" width={200} height={64} className="h-16 w-auto" priority />
            </div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-950/80 backdrop-blur-md border border-slate-700 text-[var(--color-x-cyan)] text-sm font-medium mb-6 shadow-sm relative z-10">
              <span className="w-2 h-2 rounded-full bg-[var(--color-x-cyan)]"></span>
              Manufacturing Intelligence
            </div>
            <h1 className="text-5xl md:text-6xl font-bold tracking-tight text-white mb-6 leading-tight relative z-10 bg-[#050c1e]/30 backdrop-blur-lg border border-white/10 rounded-[18px] p-6 sm:p-8 shadow-2xl">
              Know about production risks before they become delivery failures.
            </h1>
            <p className="text-lg text-white mb-8 leading-relaxed max-w-lg font-medium relative z-10 bg-[#050c1e]/35 backdrop-blur-md border border-white/10 rounded-2xl px-6 py-5 shadow-xl">
              Turn fragmented factory signals into clear, evidence-backed production intelligence. We connect your structured ERP data with shop-floor WhatsApp communication to identify what went wrong, why it happened, and which customer orders are at risk.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 relative z-10">
              <button onClick={openPilotModal} className="inline-flex justify-center items-center gap-2 bg-[var(--color-x-teal)] hover:bg-teal-500 text-white px-6 py-3 rounded-md font-semibold transition-colors shadow-lg w-full sm:w-auto">Book a Pilot<ArrowRight className="w-4 h-4" /></button>
              <Link href="/how-it-works" className="inline-flex justify-center items-center gap-2 bg-slate-900/90 backdrop-blur-sm hover:bg-slate-800 border border-slate-600 text-white px-6 py-3 rounded-md font-semibold transition-colors shadow-lg">
                See How It Works
              </Link>
            </div>
          </div>
          <div className="relative mt-12 lg:mt-0">
            <style>{`
              @keyframes liveGlow {
                0%, 100% { box-shadow: 0 0 0 rgba(0,0,0,0); border-color: rgba(255,255,255,0.05); transform: scale(1); }
                5% { box-shadow: 0 0 20px var(--glow-color); border-color: var(--glow-color); transform: scale(1.01); }
                20% { box-shadow: 0 0 0 rgba(0,0,0,0); border-color: rgba(255,255,255,0.05); transform: scale(1); }
              }
              @keyframes liveSignalY {
                0%, 100% { opacity: 0; transform: translateY(-100%); }
                5% { opacity: 1; transform: translateY(0%); }
                15% { opacity: 0; transform: translateY(100%); }
              }
              @keyframes liveSignalBranch {
                0%, 100% { opacity: 0; transform: scaleX(0); }
                5% { opacity: 1; transform: scaleX(1); }
                15% { opacity: 0; transform: scaleX(1); }
              }
              .live-glow {
                animation: liveGlow 5s infinite ease-in-out;
              }
              .live-signal-y {
                animation: liveSignalY 5s infinite ease-in-out;
              }
              .live-signal-branch {
                animation: liveSignalBranch 5s infinite ease-in-out;
                transform-origin: center;
              }
              @media (prefers-reduced-motion: reduce) {
                .live-glow, .live-signal-y, .live-signal-branch {
                  animation: none !important;
                  opacity: 0.8 !important;
                  transform: none !important;
                  border-color: var(--glow-color) !important;
                }
              }
            `}</style>
            <div className="bg-[#080f23]/50 backdrop-blur-md border border-white/10 shadow-2xl rounded-2xl p-8 relative z-10 flex flex-col items-center">
              {/* Node 1: Signal */}
              <div className="flex flex-col items-center">
                <div className="w-48 text-center bg-slate-950/60 backdrop-blur-sm border rounded-lg p-3 relative group transition-all live-glow" style={{ '--glow-color': 'var(--color-x-blue)', animationDelay: '0s' } as React.CSSProperties}>
                  <span className="text-xs font-bold text-[var(--color-x-blue)] tracking-wider uppercase block mb-1">Incoming</span>
                  <span className="text-sm text-white font-medium">Shop-Floor Signal</span>
                </div>
                {/* Connector */}
                <div className="h-10 w-px bg-slate-800/80 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-cyan)] live-signal-y" style={{ animationDelay: '0.5s' }}></div>
                </div>
              </div>

              {/* Node 2: AI Understanding */}
              <div className="flex flex-col items-center">
                <div className="w-56 text-center bg-slate-950/60 backdrop-blur-sm border rounded-lg p-3 relative group transition-all live-glow" style={{ '--glow-color': 'var(--color-x-teal)', animationDelay: '1s' } as React.CSSProperties}>
                  <span className="text-xs font-bold text-[var(--color-x-teal)] tracking-wider uppercase block mb-1">Processing</span>
                  <span className="text-sm text-white font-medium">AI Understanding</span>
                </div>
                <div className="h-10 w-px bg-slate-800/80 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-teal)] live-signal-y" style={{ animationDelay: '1.5s' }}></div>
                </div>
              </div>

              {/* Node 3: Validation */}
              <div className="flex flex-col items-center">
                <div className="w-56 text-center bg-slate-950/60 backdrop-blur-sm border rounded-lg p-3 relative group transition-all live-glow" style={{ '--glow-color': 'var(--color-x-green)', animationDelay: '2s' } as React.CSSProperties}>
                  <span className="text-xs font-bold text-[var(--color-x-green)] tracking-wider uppercase block mb-1">Confirmed</span>
                  <span className="text-sm text-white font-medium">Validation</span>
                </div>
                <div className="h-10 w-px bg-slate-800/80 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-green)] live-signal-y" style={{ animationDelay: '2.5s' }}></div>
                </div>
              </div>

              {/* Split Path: Machine & Work Order */}
              <div className="flex justify-center w-full relative">
                {/* Horizontal branch */}
                <div className="absolute top-0 w-32 h-px bg-slate-800/80">
                   <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-green)] live-signal-branch" style={{ animationDelay: '2.8s' }}></div>
                </div>
                
                <div className="flex justify-between w-64 pt-6">
                  {/* Machine */}
                  <div className="w-28 text-center bg-slate-950/60 backdrop-blur-sm border rounded-lg p-2 transition-all live-glow" style={{ '--glow-color': 'var(--color-x-teal)', animationDelay: '3s' } as React.CSSProperties}>
                    <span className="text-[10px] text-slate-300 uppercase block">Entity</span>
                    <span className="text-sm font-bold text-white">Machine</span>
                  </div>
                  
                  {/* Work Order */}
                  <div className="w-28 text-center bg-slate-950/60 backdrop-blur-sm border rounded-lg p-2 transition-all live-glow" style={{ '--glow-color': 'var(--color-x-teal)', animationDelay: '3s' } as React.CSSProperties}>
                    <span className="text-[10px] text-slate-300 uppercase block">Impact</span>
                    <span className="text-sm font-bold text-white">Work Order</span>
                  </div>
                </div>
              </div>

              {/* Final Connector to Risk */}
              <div className="flex flex-col items-center mt-6">
                <div className="h-10 w-px bg-slate-800/80 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-amber)] live-signal-y" style={{ animationDelay: '3.5s' }}></div>
                </div>
                {/* Node 4: Risk */}
                <div className="w-48 text-center bg-[var(--color-x-amber)]/10 backdrop-blur-sm border rounded-lg p-4 live-glow" style={{ '--glow-color': 'var(--color-x-amber)', animationDelay: '4s' } as React.CSSProperties}>
                  <span className="text-xs font-bold text-[var(--color-x-amber)] tracking-wider uppercase block mb-1">Outcome</span>
                  <span className="text-lg font-bold text-white">Risk Decision</span>
                </div>
              </div>
            </div>
            {/* Abstract visual elements */}
            <div className="absolute -top-10 -right-10 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl"></div>
            <div className="absolute -bottom-10 -left-10 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl"></div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Ecosystem() {
  return (
    <section className="py-12 bg-transparent">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-[#080f23]/50 backdrop-blur-md border border-white/10 shadow-2xl rounded-2xl p-8 md:p-12 text-center">
          <h2 className="text-sm font-semibold text-slate-400 tracking-wider uppercase mb-8">BUILT FOR THE REALITY OF MODERN FACTORIES</h2>
          <div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-6 text-slate-200 font-medium text-lg">
            <span className="flex items-center gap-2"><DatabaseIcon /> ERP / Tally</span>
            <span className="text-slate-500">+</span>
            <span className="flex items-center gap-2"><TableIcon /> Excel / CSV</span>
            <span className="text-slate-500">+</span>
            <span className="flex items-center gap-2"><MessageCircleIcon /> WhatsApp</span>
            <span className="text-slate-500">+</span>
            <span className="flex items-center gap-2"><BrainCircuitIcon /> AI</span>
            <span className="text-slate-500">+</span>
            <span className="flex items-center gap-2"><ShieldCheckIcon /> Evidence</span>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Problem() {
  return (
    <section className="py-24 bg-transparent">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-4xl mx-auto mb-16 bg-[#080f23]/50 backdrop-blur-md border border-white/10 shadow-2xl rounded-2xl p-8 md:p-12">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
            Your factory already has the data. The problem is connecting it in time.
          </h2>
          <p className="text-lg text-slate-400">
            Important operational changes are often buried inside fragmented communication and structured systems. The problem isn't that factories use WhatsApp. The problem is fragmented operational context.
          </p>
        </div>
        <div className="relative">
          <div className="hidden md:block absolute top-1/2 left-0 w-full h-px bg-slate-800 -translate-y-1/2 z-0"></div>
          <div className="grid md:grid-cols-4 gap-8 relative z-10">
            {[
              { title: "Machine Issue", desc: "Buried in a WhatsApp voice note from the floor." },
              { title: "Production Delay", desc: "Not updated in the ERP until the shift ends." },
              { title: "Work-Order Risk", desc: "Planning doesn't know capacity has dropped." },
              { title: "Delivery Failure", desc: "Customer escalates. Management finds out last." }
            ].map((step, i) => (
              <div key={i} className="bg-slate-900/50 backdrop-blur-md border border-white/10 p-6 rounded-xl shadow-sm relative">
                <div className="w-8 h-8 rounded-full bg-white text-slate-900 flex items-center justify-center font-bold text-sm mb-4 absolute -top-4 -left-4">
                  {i + 1}
                </div>
                <h3 className="text-lg font-bold text-white mb-2">{step.title}</h3>
                <p className="text-sm text-slate-400">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export function ProductThesis() {
  return (
    <section className="py-24 bg-transparent border-t border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div className="bg-[#080f23]/50 backdrop-blur-md border border-white/10 shadow-2xl rounded-2xl p-8 md:p-12">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
              From fragmented factory signals to one operational picture.
            </h2>
            <p className="text-lg text-slate-400 mb-8">
              "Keep your factory workflow. Add intelligence to it." Xaiote is an intelligence layer over existing manufacturing workflows, designed to minimize workflow change.
            </p>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-6 h-6 text-[var(--color-x-teal)] shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-white">What Xaiote is</h4>
                  <p className="text-sm text-slate-400">Production-risk intelligence, root-cause investigation, and evidence-first decision support.</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <XCircle className="w-6 h-6 text-red-500 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-white">What Xaiote is NOT</h4>
                  <p className="text-sm text-slate-400">Not an ERP replacement, not an MES replacement, not a generic chatbot. Designed to work with your existing systems, not replace them.</p>
                </div>
              </div>
            </div>
          </div>
          <div className="bg-slate-900/40 backdrop-blur-md p-8 rounded-2xl shadow-xl border border-white/10">
            <div className="space-y-6">
              <div className="flex items-center gap-4 p-4 bg-slate-950/80 rounded-lg border border-slate-800">
                <div className="w-12 h-12 rounded-full bg-blue-900/30 flex items-center justify-center shrink-0">
                  <DatabaseIcon className="w-6 h-6 text-[var(--color-x-blue)]" />
                </div>
                <div>
                  <h5 className="font-medium text-white">Structured Data</h5>
                  <p className="text-xs text-slate-400">CSV, Excel, ERP exports</p>
                </div>
              </div>
              <div className="flex justify-center"><ArrowDownIcon className="text-slate-500" /></div>
              <div className="flex items-center gap-4 p-4 bg-slate-950/80 rounded-lg border border-[var(--color-x-cyan)]/30 shadow-md">
                <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center shrink-0 border border-[var(--color-x-cyan)]/50 shadow-[0_0_10px_rgba(6,182,212,0.3)]">
                  <span className="font-bold text-[var(--color-x-cyan)]">X</span>
                </div>
                <div>
                  <h5 className="font-medium text-white">Xaiote Intelligence Layer</h5>
                  <p className="text-xs text-slate-400">Entity resolution & impact analysis</p>
                </div>
              </div>
              <div className="flex justify-center"><ArrowUpIcon className="text-slate-500" /></div>
              <div className="flex items-center gap-4 p-4 bg-slate-950/80 rounded-lg border border-slate-800">
                <div className="w-12 h-12 rounded-full bg-green-900/30 flex items-center justify-center shrink-0">
                  <MessageCircleIcon className="w-6 h-6 text-[var(--color-x-green)]" />
                </div>
                <div>
                  <h5 className="font-medium text-white">Unstructured Signals</h5>
                  <p className="text-xs text-slate-400">WhatsApp text & voice from the floor</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// Minimal stub icons for self-containment
const DatabaseIcon = (props:any) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/></svg>;
const TableIcon = (props:any) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M9 3v18"/><path d="M15 3v18"/></svg>;
const MessageCircleIcon = (props:any) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>;
const BrainCircuitIcon = (props:any) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M9 13a4.5 4.5 0 0 0 3-4"/><path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/><path d="M3.477 10.896a4 4 0 0 1 .585-.396"/><path d="M6 18a4 4 0 0 1-1.967-.516"/><path d="M12 13h4"/><path d="M12 17h4"/><path d="M16 11h2"/><path d="M16 15h2"/></svg>;
const ShieldCheckIcon = (props:any) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/></svg>;
const ArrowDownIcon = (props:any) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></svg>;
const ArrowUpIcon = (props:any) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 7-7 7 7"/><path d="M12 19V5"/></svg>;
