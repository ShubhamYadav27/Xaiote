"use client";
import { Target, ArrowRight, UserCheck, ShieldCheck, Activity, Eye, CheckCircle2, ArrowDown } from "lucide-react";

export function RiskIntelligence() {
  const states = [
    { name: "ON TRACK", desc: "No material disruption identified", color: "var(--color-x-green)", bg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-500" },
    { name: "AT RISK", desc: "Potential production impact identified", color: "var(--color-x-amber)", bg: "bg-amber-500/10 border-amber-500/30 text-amber-500" },
    { name: "DELAYED", desc: "Evidence indicates delivery is likely affected", color: "var(--color-x-orange)", bg: "bg-orange-500/10 border-orange-500/30 text-orange-500" },
    { name: "CRITICAL", desc: "Severe operational impact requiring immediate attention", color: "var(--color-x-red)", bg: "bg-red-500/10 border-red-500/30 text-red-500" },
  ];

  return (
    <section className="py-24 bg-transparent">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 text-center">
          Risk states reflect current evidence and business impact.
        </h2>
        <p className="text-center text-slate-400 mb-16 max-w-2xl mx-auto">Orders do not blindly progress through every stage. Xaiote assigns deterministic states based on real-time disruption data.</p>
        
        <div className="flex flex-col md:flex-row justify-center items-stretch gap-4 max-w-6xl mx-auto">
          {states.map((state) => (
            <div key={state.name} className="flex-1 p-6 rounded-2xl border border-white/10 hover:shadow-lg transition-all flex flex-col justify-between group bg-slate-900/50 backdrop-blur-md relative overflow-hidden"
              style={{ '--state-color': state.color } as React.CSSProperties}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = state.color;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e2e8f0';
              }}
            >
              <div className="absolute top-0 right-0 w-24 h-24 rounded-bl-full opacity-5 transition-opacity group-hover:opacity-10" style={{ backgroundColor: state.color }}></div>
              <div>
                <div className={`inline-block px-3 py-1 text-xs font-bold rounded mb-4 ${state.bg}`}>
                  {state.name}
                </div>
                <p className="text-sm text-slate-300 font-medium mb-4 relative z-10">{state.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function DashboardPreview() {
  return (
    <section className="py-24 bg-transparent overflow-hidden relative">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-[var(--color-x-cyan)]/5 rounded-full blur-3xl -z-10"></div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center mb-16 relative z-10">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
          Give management the answer, not another data dump.
        </h2>
        <p className="text-lg text-slate-400 max-w-2xl mx-auto">
          Know instantly which orders are at risk, why, and how much impact it will have.
        </p>
      </div>
      
      <div className="max-w-6xl mx-auto bg-slate-950 rounded-2xl border border-slate-800 shadow-2xl overflow-hidden relative z-10">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80 backdrop-blur">
          <div className="flex space-x-2">
            <div className="w-3 h-3 rounded-full bg-slate-700"></div>
            <div className="w-3 h-3 rounded-full bg-slate-700"></div>
            <div className="w-3 h-3 rounded-full bg-slate-700"></div>
          </div>
          <div className="text-xs text-slate-400 font-mono tracking-widest uppercase">Illustrative Dashboard Data</div>
        </div>
        <div className="p-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-transparent border border-slate-800 rounded-xl p-5 shadow-inner">
              <div className="text-slate-400 text-sm mb-1 font-medium">Active Orders</div>
              <div className="text-3xl font-bold text-white">142</div>
            </div>
            <div className="bg-transparent border border-slate-800 rounded-xl p-5 shadow-[inset_0_0_15px_rgba(245,158,11,0.05)]">
              <div className="text-slate-400 text-sm mb-1 font-medium">At-Risk Orders</div>
              <div className="text-3xl font-bold text-[var(--color-x-amber)]">3</div>
            </div>
            <div className="bg-transparent border border-slate-800 rounded-xl p-5 shadow-[inset_0_0_15px_rgba(249,115,22,0.05)]">
              <div className="text-slate-400 text-sm mb-1 font-medium">Delayed Orders</div>
              <div className="text-3xl font-bold text-[var(--color-x-orange)]">1</div>
            </div>
            <div className="bg-transparent border border-slate-800 rounded-xl p-5 shadow-[inset_0_0_15px_rgba(239,68,68,0.05)]">
              <div className="text-slate-400 text-sm mb-1 font-medium">Critical Issues</div>
              <div className="text-3xl font-bold text-[var(--color-x-red)]">1</div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-800 uppercase tracking-wider text-xs">
                  <th className="pb-3 font-semibold">Order</th>
                  <th className="pb-3 font-semibold">Customer</th>
                  <th className="pb-3 font-semibold">Delivery</th>
                  <th className="pb-3 font-semibold">Risk State</th>
                  <th className="pb-3 font-semibold">Root Cause</th>
                  <th className="pb-3 font-semibold">Machine</th>
                  <th className="pb-3 font-semibold">Delay</th>
                </tr>
              </thead>
              <tbody className="text-slate-400">
                <tr className="border-b border-slate-800/50 hover:bg-slate-800/50 transition-colors group cursor-default">
                  <td className="py-4 font-mono font-medium group-hover:text-white transition-colors">WO-1045</td>
                  <td className="py-4 group-hover:text-white transition-colors">ABC Motors</td>
                  <td className="py-4">Tomorrow</td>
                  <td className="py-4"><span className="px-2 py-1 bg-[var(--color-x-amber)]/10 border border-[var(--color-x-amber)]/30 text-[var(--color-x-amber)] text-xs font-bold rounded shadow-[0_0_10px_rgba(245,158,11,0.2)]">AT RISK</span></td>
                  <td className="py-4 group-hover:text-white transition-colors">Spindle Failure</td>
                  <td className="py-4 font-mono group-hover:text-[var(--color-x-cyan)] transition-colors">CNC-02</td>
                  <td className="py-4 text-red-400 group-hover:text-red-300 transition-colors">8h</td>
                </tr>
                <tr className="border-b border-slate-800/50 hover:bg-slate-800/50 transition-colors group cursor-default">
                  <td className="py-4 font-mono font-medium group-hover:text-white transition-colors">WO-1048</td>
                  <td className="py-4 group-hover:text-white transition-colors">XYZ Auto</td>
                  <td className="py-4">2 days</td>
                  <td className="py-4"><span className="px-2 py-1 bg-[var(--color-x-orange)]/10 border border-[var(--color-x-orange)]/30 text-[var(--color-x-orange)] text-xs font-bold rounded">DELAYED</span></td>
                  <td className="py-4 group-hover:text-white transition-colors">Material Delay</td>
                  <td className="py-4 text-slate-500">—</td>
                  <td className="py-4 text-orange-400 group-hover:text-orange-300 transition-colors">24h</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}

export function AlertsAction() {
  return (
    <section className="py-24 bg-transparent border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
            Human in the loop. Always.
          </h2>
          <p className="text-lg text-slate-400">
            Xaiote does not autonomously change critical production state or customer commitments.
          </p>
        </div>
        
        {/* Human-in-the-loop flow */}
        <div className="max-w-4xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm font-bold text-slate-300 bg-slate-900/50 backdrop-blur-md p-6 rounded-xl border border-white/10">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-[var(--color-x-cyan)]" /> AI Understands
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400 hidden md:block" /><ArrowDown className="w-4 h-4 text-slate-400 md:hidden" />
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-[var(--color-x-green)]" /> System Validates
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400 hidden md:block" /><ArrowDown className="w-4 h-4 text-slate-400 md:hidden" />
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-[var(--color-x-amber)]" /> Risk Determined
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400 hidden md:block" /><ArrowDown className="w-4 h-4 text-slate-400 md:hidden" />
          <div className="flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-[var(--color-x-blue)]" /> Human Reviews
          </div>
        </div>
      </div>
    </section>
  );
}

export function RoleSolutions() {
  const roles = [
    { name: "Owner / MD", need: "Visibility into business disruption risk.", surface: "Risk state, critical orders, top causes.", decision: "Capital allocation & customer comms." },
    { name: "Plant Head", need: "Know what requires intervention.", surface: "At-risk orders, bottleneck machines.", decision: "Resource reallocation." },
    { name: "Production", need: "Manage schedule and constraints.", surface: "Order impact, allocation, remaining buffer.", decision: "Sequence changes." },
    { name: "Maintenance", need: "Respond to machine issues.", surface: "Machine incidents, affected work orders.", decision: "Prioritization of repair." },
  ];

  return (
    <section className="py-24 bg-slate-900/50 backdrop-blur-md border-t border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl font-bold text-white mb-12 text-center">Intelligence for every role</h2>
        <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
          {roles.map((role) => (
            <div key={role.name} className="bg-transparent p-6 rounded-2xl border border-white/10 shadow-sm hover:border-[var(--color-x-teal)] transition-colors group">
              <h3 className="font-bold text-xl text-white mb-6 border-b border-slate-800 pb-4 flex items-center justify-between">
                {role.name}
                <Eye className="w-5 h-5 text-slate-400 group-hover:text-[var(--color-x-teal)] transition-colors" />
              </h3>
              <div className="space-y-4">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">What They Need</span>
                  <span className="text-sm text-slate-300">{role.need}</span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-[var(--color-x-teal)] uppercase tracking-widest font-bold">What Xaiote Surfaces</span>
                  <span className="text-sm font-medium text-white bg-slate-900/50 backdrop-blur-md p-2 rounded border border-slate-800">{role.surface}</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[var(--color-x-green)]" />
                  <span className="text-sm text-slate-400">Supports: <strong>{role.decision}</strong></span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function Industries() {
  return (
    <section className="py-24 bg-transparent border-t border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="bg-[#080f23]/50 backdrop-blur-md border border-white/10 shadow-2xl rounded-2xl p-8 md:p-12 max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-white mb-6">Designed initially for manufacturing environments</h2>
          <div className="flex flex-wrap justify-center gap-3 max-w-4xl mx-auto mt-8">
            {["Automotive Components", "CNC Machining", "Casting", "Forging", "Sheet Metal", "Fabrication", "Injection Molding", "Industrial Equipment"].map((industry) => (
              <span key={industry} className="px-4 py-2 bg-slate-900/50 backdrop-blur-md text-slate-300 rounded-lg text-sm font-medium border border-white/10 hover:border-[var(--color-x-teal)] hover:text-[var(--color-x-teal)] transition-colors cursor-default">
                {industry}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
