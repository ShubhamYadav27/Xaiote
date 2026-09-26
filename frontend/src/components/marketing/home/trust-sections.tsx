import { ShieldCheck, Database, RefreshCw, Lock, ArrowRight, Activity, ArrowDown, UserCheck, TrendingUp } from "lucide-react";

export function SystemEcosystem() {
  return (
    <section className="py-24 bg-transparent text-white overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-20">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">Works with the systems your factory already uses.</h2>
          <p className="text-lg text-slate-300">Connect fragmented factory signals into one operational picture.</p>
        </div>
        
        <style>{`
          @keyframes liveGlow {
            0%, 100% { box-shadow: 0 0 0 rgba(0,0,0,0); border-color: rgba(255,255,255,0.05); transform: scale(1); }
            5% { box-shadow: 0 0 20px var(--glow-color); border-color: var(--glow-color); transform: scale(1.02); }
            20% { box-shadow: 0 0 0 rgba(0,0,0,0); border-color: rgba(255,255,255,0.05); transform: scale(1); }
          }
          @keyframes liveSignalX {
            0%, 100% { opacity: 0; transform: translateX(-100%); }
            5% { opacity: 1; transform: translateX(0%); }
            15% { opacity: 0; transform: translateX(100%); }
          }
          @keyframes liveSvgPulse {
            0%, 100% { stroke-dashoffset: 100; opacity: 0; }
            5% { opacity: 1; }
            20% { stroke-dashoffset: -30; opacity: 0; }
          }
          .live-glow {
            animation: liveGlow 5s infinite ease-in-out;
          }
          .live-signal-x {
            animation: liveSignalX 5s infinite ease-in-out;
          }
          .live-svg-pulse {
            stroke-dasharray: 30 100;
            animation: liveSvgPulse 5s infinite ease-in-out;
          }
          @media (prefers-reduced-motion: reduce) {
            .live-glow, .live-signal-x, .live-svg-pulse {
              animation: none !important;
              opacity: 0.8 !important;
              transform: none !important;
              border-color: var(--glow-color) !important;
              stroke-dashoffset: 0 !important;
            }
          }
        `}</style>
        <div className="max-w-4xl mx-auto relative">
          <div className="grid md:grid-cols-3 gap-8 items-center">
            {/* Left Inputs */}
            <div className="flex flex-col gap-6">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-center relative transition-all flex flex-col justify-center h-full min-h-[64px] live-glow" style={{ '--glow-color': 'var(--color-x-cyan)', animationDelay: '0s' } as React.CSSProperties}>
                <span className="font-bold text-slate-400 transition-colors">ERP / Tally</span>
                <div className="absolute top-1/2 -right-4 w-4 h-px bg-slate-800 md:hidden"></div>
                <svg className="absolute top-1/2 left-full w-8 h-[calc(100%+1.5rem)] hidden md:block pointer-events-none" viewBox="0 0 32 100" preserveAspectRatio="none">
                  <path d="M0,0 C16,0 16,100 32,100" fill="none" stroke="#1e293b" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
                  <path className="live-svg-pulse" d="M0,0 C16,0 16,100 32,100" pathLength="100" fill="none" stroke="var(--color-x-cyan)" strokeWidth="2" vectorEffect="non-scaling-stroke" style={{ animationDelay: '0.5s' }} />
                </svg>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-center relative z-10 flex flex-col justify-center h-full min-h-[64px] live-glow" style={{ '--glow-color': 'var(--color-x-cyan)', animationDelay: '0.2s' } as React.CSSProperties}>
                <span className="font-bold text-slate-400">Excel / CSV</span>
                <div className="absolute top-1/2 -right-8 w-8 h-px bg-slate-800 hidden md:block overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-cyan)] live-signal-x" style={{ animationDelay: '0.7s' }}></div>
                </div>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-center relative transition-all flex flex-col justify-center h-full min-h-[64px] live-glow" style={{ '--glow-color': 'var(--color-x-cyan)', animationDelay: '0.4s' } as React.CSSProperties}>
                <span className="font-bold text-slate-400 transition-colors">WhatsApp Text/Voice</span>
                <div className="absolute top-1/2 -right-4 w-4 h-px bg-slate-800 md:hidden"></div>
                <svg className="absolute bottom-1/2 left-full w-8 h-[calc(100%+1.5rem)] hidden md:block pointer-events-none" viewBox="0 0 32 100" preserveAspectRatio="none">
                  <path d="M0,100 C16,100 16,0 32,0" fill="none" stroke="#1e293b" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
                  <path className="live-svg-pulse" d="M0,100 C16,100 16,0 32,0" pathLength="100" fill="none" stroke="var(--color-x-cyan)" strokeWidth="2" vectorEffect="non-scaling-stroke" style={{ animationDelay: '0.9s' }} />
                </svg>
              </div>
            </div>

            {/* Middle System */}
            <div className="relative">
               <div className="bg-gradient-to-b from-slate-900 to-slate-950 p-8 rounded-2xl border text-center relative z-10 flex flex-col justify-center live-glow" style={{ '--glow-color': 'var(--color-x-teal)', animationDelay: '1.2s' } as React.CSSProperties}>
                 <div className="w-16 h-16 bg-transparent rounded-full flex items-center justify-center mx-auto mb-4 border border-[var(--color-x-teal)]">
                   <Activity className="w-8 h-8 text-[var(--color-x-teal)]" />
                 </div>
                 <h3 className="font-bold text-xl text-white mb-2">Xaiote Intelligence</h3>
                 <p className="text-xs text-slate-400 uppercase tracking-widest">Evidence</p>
                 <div className="absolute top-1/2 -right-8 w-8 h-px bg-slate-800 hidden md:block overflow-hidden">
                   <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-teal)] live-signal-x" style={{ animationDelay: '1.7s' }}></div>
                 </div>
               </div>
               {/* Mobile arrow */}
               <div className="flex justify-center md:hidden my-4"><ArrowDown className="text-slate-300"/></div>
            </div>

            {/* Right Output */}
            <div className="flex flex-col justify-center h-full">
              <div className="bg-transparent/40 backdrop-blur-md p-6 rounded-2xl border text-center live-glow" style={{ '--glow-color': 'var(--color-x-amber)', animationDelay: '2.2s' } as React.CSSProperties}>
                <span className="text-[10px] text-[var(--color-x-amber)] uppercase tracking-widest block mb-2 font-bold">Outcome</span>
                <span className="font-bold text-xl text-white block">Production Risk</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function AITrust() {
  return (
    <section className="py-24 bg-transparent overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">AI does not create facts.</h2>
          <p className="text-lg text-slate-400">
            AI that understands factory context — strictly controlled by deterministic validation.
          </p>
        </div>
        
        {/* Pipeline Visual */}
        <div className="max-w-5xl mx-auto mb-16 bg-transparent border border-white/10 rounded-xl p-6 overflow-x-auto">
          <div className="flex items-center min-w-[700px] justify-between text-sm font-bold uppercase tracking-wider">
            <div className="flex flex-col items-center gap-2">
              <span className="text-slate-400">Source</span>
              <div className="w-4 h-4 rounded-full bg-slate-700 border border-transparent live-glow" style={{ '--glow-color': 'white', animationDelay: '0s' } as React.CSSProperties}></div>
            </div>
            <div className="h-px bg-slate-700 flex-1 mx-2 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-cyan)] live-signal-x" style={{ animationDelay: '0.5s' }}></div>
            </div>
            <div className="flex flex-col items-center gap-2">
              <span className="text-[var(--color-x-cyan)]">AI Understanding</span>
              <div className="w-4 h-4 rounded-full bg-[var(--color-x-cyan)]/20 border-2 border-transparent live-glow" style={{ '--glow-color': 'var(--color-x-cyan)', animationDelay: '1s' } as React.CSSProperties}></div>
            </div>
            <div className="h-px bg-slate-700 flex-1 mx-2 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-green)] live-signal-x" style={{ animationDelay: '1.5s' }}></div>
            </div>
            <div className="flex flex-col items-center gap-2">
              <span className="text-[var(--color-x-green)]">Validation</span>
              <div className="w-4 h-4 rounded-full bg-[var(--color-x-green)] border border-transparent live-glow" style={{ '--glow-color': 'var(--color-x-green)', animationDelay: '2s' } as React.CSSProperties}></div>
            </div>
            <div className="h-px bg-slate-700 flex-1 mx-2 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-teal)] live-signal-x" style={{ animationDelay: '2.5s' }}></div>
            </div>
            <div className="flex flex-col items-center gap-2 text-center">
              <span className="text-white">Deterministic<br/>Business Logic</span>
              <div className="w-4 h-4 rounded-none bg-slate-800 rotate-45 border border-transparent live-glow" style={{ '--glow-color': 'white', animationDelay: '3s' } as React.CSSProperties}></div>
            </div>
            <div className="h-px bg-slate-700 flex-1 mx-2 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-blue)] live-signal-x" style={{ animationDelay: '3.5s' }}></div>
            </div>
            <div className="flex flex-col items-center gap-2">
              <span className="text-[var(--color-x-blue)]">Human Confirmation</span>
              <div className="w-4 h-4 rounded bg-[var(--color-x-blue)] border border-transparent live-glow" style={{ '--glow-color': 'var(--color-x-blue)', animationDelay: '4s' } as React.CSSProperties}></div>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-12 max-w-4xl mx-auto">
          <div className="bg-transparent p-8 rounded-xl border border-white/10">
            <h3 className="font-bold text-[var(--color-x-teal)] mb-4 flex items-center gap-2"><ShieldCheck className="w-5 h-5"/> AI Can:</h3>
            <ul className="space-y-3 text-sm text-slate-300">
              <li>• Extract entities (Machines, Parts)</li>
              <li>• Classify events and root causes</li>
              <li>• Interpret justified relative time</li>
              <li>• Suggest candidate relationships</li>
              <li>• Generate human-readable explanations</li>
            </ul>
          </div>
          <div className="bg-red-950/20 backdrop-blur-md p-8 rounded-xl border border-red-900/30">
            <h3 className="font-bold text-red-700 mb-4 flex items-center gap-2"><Lock className="w-5 h-5"/> AI Must NOT:</h3>
            <ul className="space-y-3 text-sm text-red-300/80">
              <li>• Invent downtime or machine states</li>
              <li>• Invent delivery dates or customer impact</li>
              <li>• Directly mutate critical production state</li>
              <li>• Change customer commitments autonomously</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Security() {
  return (
    <section className="py-24 bg-transparent border-t border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl font-bold text-white mb-12 text-center">Security, Trust & Governance</h2>
        
        {/* Security Pipeline visual */}
        <div className="max-w-4xl mx-auto mb-16 relative">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 relative z-10">
            <div className="bg-transparent px-4 py-3 rounded-lg border border-white/10 shadow-sm text-sm font-bold text-slate-300">Official WhatsApp Business</div>
            <ArrowRight className="w-5 h-5 text-slate-400 hidden md:block" />
            <ArrowDown className="w-5 h-5 text-slate-400 md:hidden" />
            <div className="bg-transparent px-4 py-3 rounded-lg border border-white/10 shadow-sm text-sm font-bold text-slate-300">Verified Webhook</div>
            <ArrowRight className="w-5 h-5 text-slate-400 hidden md:block" />
            <ArrowDown className="w-5 h-5 text-slate-400 md:hidden" />
            <div className="bg-transparent px-4 py-3 rounded-lg border border-[var(--color-x-cyan)] shadow-sm text-sm font-bold text-[var(--color-x-cyan)]">Controlled Processing</div>
            <ArrowRight className="w-5 h-5 text-slate-400 hidden md:block" />
            <ArrowDown className="w-5 h-5 text-slate-400 md:hidden" />
            <div className="bg-transparent px-4 py-3 rounded-lg border border-slate-700 shadow-sm text-sm font-bold text-white">XAIOTE</div>
          </div>
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[var(--color-x-teal)]/5 to-transparent blur-xl -z-10 rounded-full"></div>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-transparent p-6 rounded-xl border border-white/10">
            <Lock className="w-8 h-8 text-[var(--color-x-teal)] mb-4" />
            <h3 className="font-bold text-white mb-2">Tenant Isolation</h3>
            <p className="text-sm text-slate-400">Data is strictly isolated. Models do not train on your production data.</p>
          </div>
          <div className="bg-transparent p-6 rounded-xl border border-white/10">
            <ShieldCheck className="w-8 h-8 text-[var(--color-x-teal)] mb-4" />
            <h3 className="font-bold text-white mb-2">Verified Processing</h3>
            <p className="text-sm text-slate-400">Webhook verification, encryption in transit, and least-privilege architecture.</p>
          </div>
          <div className="bg-transparent p-6 rounded-xl border border-white/10">
            <Database className="w-8 h-8 text-[var(--color-x-teal)] mb-4" />
            <h3 className="font-bold text-white mb-2">Audit Logging</h3>
            <p className="text-sm text-slate-400">Every action, validation, and human confirmation is securely logged.</p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function DataFreshness() {
  return (
    <section className="py-24 bg-transparent border-t border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <RefreshCw className="w-12 h-12 text-slate-400 mx-auto mb-6" />
        <h2 className="text-3xl font-bold text-white mb-4">Know when your data was last updated.</h2>
        <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-8">
          Stale data should never silently appear current. Xaiote shows exact freshness metadata and prioritizes recent verified events over old CSV imports.
        </p>
        <div className="inline-flex items-center gap-2 bg-transparent/60 border border-white/10 backdrop-blur-md px-4 py-2 rounded-lg text-sm font-medium text-slate-300">
          Manual Override &gt; Recent Verified Event &gt; Latest Imported Data
        </div>
      </div>
    </section>
  );
}

export function HumanInTheLoop() {
  return (
    <section className="py-24 bg-transparent text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <UserCheck className="w-12 h-12 text-teal-500 mx-auto mb-6" />
        <h2 className="text-3xl font-bold mb-4">Automation where confidence is high. <br className="hidden md:block"/> Human control where it matters.</h2>
        <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-12">
          Low confidence alerts demand explicit human confirmation. You always have the ability to confirm, reject, edit, or override system assessments.
        </p>
      </div>
    </section>
  );
}

export function ROI() {
  return (
    <section className="py-24 bg-transparent border-t border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <TrendingUp className="w-12 h-12 text-teal-600 mx-auto mb-6" />
          <h2 className="text-3xl font-bold text-white mb-4">Measure the operational value of earlier visibility.</h2>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto">
            Evaluate Xaiote during a pilot by measuring tangible improvements in operational latency.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {["Event-to-Alert Latency", "At-Risk Orders Recovered", "Coordination Cost Saved"].map((metric) => (
            <div key={metric} className="bg-transparent p-6 rounded-xl border border-white/10 text-center font-semibold text-white shadow-sm">
              {metric}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
