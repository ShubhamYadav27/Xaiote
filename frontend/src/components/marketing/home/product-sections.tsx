"use client";
import { FileText, Activity, MessageSquare, Database, ArrowDown, ChevronRight } from "lucide-react";
import { useState } from "react";

export function ArchitectureFlow() {
  return (
    <section className="py-24 bg-transparent border-y border-white/10 overflow-hidden">
      <style>{`
        @keyframes liveGlow {
          0%, 100% { box-shadow: 0 0 0 rgba(0,0,0,0); border-color: rgba(255,255,255,0.05); transform: scale(1); }
          5% { box-shadow: 0 0 20px var(--glow-color); border-color: var(--glow-color); transform: scale(1.02); }
          20% { box-shadow: 0 0 0 rgba(0,0,0,0); border-color: rgba(255,255,255,0.05); transform: scale(1); }
        }
        @keyframes liveSignalY {
          0%, 100% { opacity: 0; transform: translateY(-100%); }
          5% { opacity: 1; transform: translateY(0%); }
          15% { opacity: 0; transform: translateY(100%); }
        }
        @keyframes liveSignalX {
          0%, 100% { opacity: 0; transform: translateX(-100%); }
          5% { opacity: 1; transform: translateX(0%); }
          15% { opacity: 0; transform: translateX(100%); }
        }
        .live-glow {
          animation: liveGlow 5s infinite ease-in-out;
        }
        .live-signal-y {
          animation: liveSignalY 5s infinite ease-in-out;
        }
        .live-signal-x {
          animation: liveSignalX 5s infinite ease-in-out;
        }
        @media (prefers-reduced-motion: reduce) {
          .live-glow, .live-signal-y, .live-signal-x {
            animation: none !important;
            opacity: 0.8 !important;
            transform: none !important;
            border-color: var(--glow-color) !important;
          }
        }
      `}</style>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-20">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
            The Intelligence Pipeline
          </h2>
          <p className="text-lg text-slate-300">
            Connecting fragmented factory signals into one evidence-backed risk decision.
          </p>
        </div>

        <div className="max-w-5xl mx-auto">
          {/* Top Inputs */}
          <div className="flex justify-center gap-16 md:gap-32 mb-8">
            <div className="flex flex-col items-center">
              <div className="w-40 text-center bg-slate-900/50 backdrop-blur-md border rounded-xl p-4 transition-all group live-glow" style={{ '--glow-color': 'var(--color-x-blue)', animationDelay: '0s' } as React.CSSProperties}>
                <Database className="w-6 h-6 text-slate-400 mx-auto mb-2 transition-colors" />
                <span className="font-bold text-white text-sm block">ERP / Excel / CSV</span>
                <span className="text-[10px] text-slate-500 uppercase mt-1">Structured</span>
              </div>
              <div className="h-8 w-px bg-slate-700 mt-4 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-blue)] live-signal-y" style={{ animationDelay: '0.5s' }}></div>
              </div>
            </div>
            
            <div className="flex flex-col items-center">
              <div className="w-40 text-center bg-slate-900/50 backdrop-blur-md border rounded-xl p-4 transition-all group live-glow" style={{ '--glow-color': 'var(--color-x-blue)', animationDelay: '0.2s' } as React.CSSProperties}>
                <MessageSquare className="w-6 h-6 text-slate-400 mx-auto mb-2 transition-colors" />
                <span className="font-bold text-white text-sm block">WhatsApp</span>
                <span className="text-[10px] text-slate-500 uppercase mt-1">Text / Voice</span>
              </div>
              <div className="h-8 w-px bg-slate-700 mt-4 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-blue)] live-signal-y" style={{ animationDelay: '0.7s' }}></div>
              </div>
            </div>
          </div>

          {/* Xaiote Engine */}
          <div className="relative border-2 border-[var(--color-x-cyan)]/20 bg-slate-900/50 backdrop-blur-md rounded-3xl p-8 max-w-4xl mx-auto group hover:border-[var(--color-x-cyan)]/50 transition-colors">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 px-4 bg-slate-900/80 backdrop-blur-sm rounded-sm whitespace-nowrap">
              <span className="text-xs font-bold text-[var(--color-x-cyan)] tracking-widest uppercase">Xaiote Intelligence</span>
            </div>

            <div className="flex flex-col items-center space-y-2">
              {/* Pipeline Nodes */}
              {[
                { name: "AI Understanding", color: "var(--color-x-cyan)" },
                { name: "Validation", color: "var(--color-x-green)" },
                { name: "Entity Resolution", color: "var(--color-x-teal)" },
                { name: "Work-Order Mapping", color: "var(--color-x-teal)" },
                { name: "Impact Analysis", color: "var(--color-x-teal)" },
                { name: "Deterministic Risk", color: "var(--color-x-amber)" },
              ].map((node, i) => (
                <div key={node.name} className="flex flex-col items-center w-full">
                  <div 
                    className="w-full max-w-sm text-center bg-transparent border rounded-lg p-3 transition-all cursor-default live-glow"
                    style={{ '--hover-color': node.color, '--glow-color': node.color, animationDelay: `${1 + i * 0.5}s` } as React.CSSProperties}
                  >
                    <span className="text-sm font-bold text-white">{node.name}</span>
                  </div>
                  {i < 5 && (
                    <div className="h-6 w-px bg-slate-800 relative overflow-hidden my-1">
                      <div className="absolute top-0 left-0 w-full h-full live-signal-y" style={{ backgroundColor: node.color, animationDelay: `${1.2 + i * 0.5}s` }}></div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Output flow */}
          <div className="flex flex-col items-center mt-0">
            <div className="h-8 w-px bg-slate-700 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-x-orange)] live-signal-y" style={{ animationDelay: '3.7s' }}></div>
            </div>
            
            <div className="flex flex-col md:flex-row gap-4 items-center">
              <div className="w-48 text-center bg-slate-900/50 backdrop-blur-md border rounded-xl p-4 live-glow" style={{ '--glow-color': 'var(--color-x-teal)', animationDelay: '4.2s' } as React.CSSProperties}>
                <span className="text-[10px] text-[var(--color-x-teal)] font-bold uppercase tracking-wider block mb-1">Explainability</span>
                <span className="font-bold text-white">Evidence</span>
              </div>
              <ArrowDown className="w-5 h-5 text-slate-400 md:-rotate-90 hidden md:block" />
              <ArrowDown className="w-5 h-5 text-slate-400 block md:hidden" />
              <div className="w-48 text-center bg-slate-900/50 backdrop-blur-md border rounded-xl p-4 live-glow" style={{ '--glow-color': 'var(--color-x-orange)', animationDelay: '4.2s' } as React.CSSProperties}>
                <span className="text-[10px] text-[var(--color-x-orange)] font-bold uppercase tracking-wider block mb-1">Notification</span>
                <span className="font-bold text-white">Alert</span>
              </div>
              <ArrowDown className="w-5 h-5 text-slate-400 md:-rotate-90 hidden md:block" />
              <ArrowDown className="w-5 h-5 text-slate-400 block md:hidden" />
              <div className="w-48 text-center bg-[var(--color-x-blue)]/5 border rounded-xl p-4 live-glow" style={{ '--glow-color': 'var(--color-x-blue)', animationDelay: '4.2s' } as React.CSSProperties}>
                <span className="text-[10px] text-[var(--color-x-blue)] font-bold uppercase tracking-wider block mb-1">Resolution</span>
                <span className="font-bold text-[var(--color-x-blue)]">Human Action</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}

export function KillerDemo() {
  const [step, setStep] = useState(1);
  const totalSteps = 9;
  
  const stepContent = [
    { title: "Incoming Signal", content: <div className="text-sm font-mono text-slate-400">"CNC 2 ka spindle toot gaya hai, maintenance wale bol rahe hain 8 ghante lagenge."</div>, type: "WhatsApp Voice" },
    { title: "AI Understanding", content: <div className="space-y-1"><div className="flex justify-between"><span className="text-slate-400">Machine:</span><span className="text-white">CNC-02</span></div><div className="flex justify-between"><span className="text-slate-400">Issue:</span><span className="text-white">Spindle Failure</span></div><div className="flex justify-between"><span className="text-slate-400">Downtime:</span><span className="text-white">8 hours</span></div></div>, type: "Extraction" },
    { title: "Validation", content: <div className="text-[var(--color-x-green)] font-medium">✓ Validated operational signal against factory constraints.</div>, type: "System" },
    { title: "Entity Resolution", content: <div className="text-white font-medium">Resolved to Entity: <span className="text-[var(--color-x-teal)]">CNC-02</span> (Lathe 3)</div>, type: "Database Map" },
    { title: "Work-Order Mapping", content: <div className="text-white font-medium">Currently active on: <span className="text-[var(--color-x-teal)]">WO-1045</span></div>, type: "Production Schedule" },
    { title: "Impact Analysis", content: <div className="space-y-1"><div className="text-white">Customer: <span className="font-bold">ABC Motors</span></div><div className="text-red-400">Delivery: Tomorrow (At Risk of Delay)</div></div>, type: "Business Logic" },
    { title: "Deterministic Risk", content: <div className="bg-[var(--color-x-amber)]/20 text-[var(--color-x-amber)] font-bold text-center py-2 rounded">AT RISK</div>, type: "Outcome" },
    { title: "Evidence", content: <div className="text-xs text-slate-400">Source: +91 98XXX XXXX<br/>Time: 14:30 IST<br/>Confidence: 98%<br/>Rule: DELAY_MARGIN &lt; 0</div>, type: "Explainability" },
    { title: "Human Action", content: <div className="flex gap-2"><button className="flex-1 bg-[var(--color-x-blue)] text-white text-xs py-2 rounded font-bold">CONFIRM</button><button className="flex-1 border border-slate-600 text-white text-xs py-2 rounded font-bold">ACKNOWLEDGE</button></div>, type: "Resolution" }
  ];

  return (
    <section className="py-24 bg-transparent text-white overflow-hidden relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            From a shop-floor message to an order-level risk.
          </h2>
          <p className="text-lg text-slate-400">
            See how Xaiote interprets a real-world disruption step-by-step. <br/>
            <span className="text-xs text-slate-500 uppercase tracking-widest mt-2 block">Illustrative demo scenario</span>
          </p>
        </div>

        <div className="max-w-4xl mx-auto bg-slate-950 border border-slate-800 rounded-2xl p-6 md:p-10 shadow-2xl">
          {/* Progress Bar */}
          <div className="flex gap-1 mb-10">
            {Array.from({ length: totalSteps }).map((_, i) => (
              <div 
                key={i} 
                className={`h-1 flex-1 rounded-full transition-colors duration-300 ${i + 1 <= step ? 'bg-[var(--color-x-cyan)]' : 'bg-slate-800'}`}
              />
            ))}
          </div>

          <div className="grid md:grid-cols-2 gap-12 items-center min-h-[250px]">
            {/* Left: Sequence UI */}
            <div>
              <div className="text-[10px] text-[var(--color-x-cyan)] font-bold uppercase tracking-widest mb-2">
                Step {step} of {totalSteps}: {stepContent[step-1].type}
              </div>
              <h3 className="text-2xl font-bold mb-6 text-white">{stepContent[step-1].title}</h3>
              
              <div className="bg-transparent border border-slate-800 p-5 rounded-xl min-h-[120px] flex flex-col justify-center transition-all">
                {stepContent[step-1].content}
              </div>
            </div>

            {/* Right: Controls */}
            <div className="flex flex-col items-center justify-center">
              <div className="text-center mb-6">
                <p className="text-sm text-slate-400 mb-2">ONE SHOP-FLOOR SIGNAL</p>
                <ArrowDown className="w-4 h-4 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-400">ONE ORDER-LEVEL RISK DECISION</p>
              </div>
              
              <div className="flex gap-4">
                <button 
                  onClick={() => setStep(Math.max(1, step - 1))}
                  disabled={step === 1}
                  className="px-6 py-3 rounded-lg font-semibold text-sm border border-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-800 transition-colors"
                >
                  Previous
                </button>
                <button 
                  onClick={() => setStep(Math.min(totalSteps, step + 1))}
                  disabled={step === totalSteps}
                  className="px-6 py-3 rounded-lg font-semibold text-sm bg-teal-500 hover:bg-teal-600 text-slate-950 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                  Next Step <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function EvidenceFirst() {
  const chain = [
    { label: "Original Source", value: "WhatsApp Voice Note" },
    { label: "Transcript", value: "CNC 2 ka spindle toot gaya hai..." },
    { label: "AI Interpretation", value: "Machine: CNC-02, Issue: Spindle, Est: 8h" },
    { label: "Entity Mapping", value: "CNC-02 → WO-1045" },
    { label: "Work-Order Impact", value: "ABC Motors - Delivery Tomorrow" },
    { label: "Risk Reason", value: "DELAY_MARGIN < 0" },
    { label: "Human Action", value: "CONFIRMED by Supervisor" }
  ];

  return (
    <section className="py-24 bg-transparent">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div className="order-2 lg:order-1 relative">
            <div className="bg-slate-900/50 backdrop-blur-md p-8 rounded-3xl border border-white/10 shadow-sm relative z-10">
              <h3 className="font-semibold text-white mb-8 flex items-center gap-2 uppercase tracking-widest text-xs">
                <FileText className="w-4 h-4 text-[var(--color-x-teal)]"/> Evidence Chain
              </h3>
              <div className="space-y-0 relative">
                <div className="absolute left-3 top-2 bottom-2 w-px bg-slate-800 z-0"></div>
                {chain.map((item, i) => (
                  <div key={i} className="flex items-start gap-4 relative z-10 group cursor-default">
                    <div className="w-6 h-6 rounded-full bg-transparent border-2 border-white/10 flex-shrink-0 mt-1 group-hover:border-[var(--color-x-teal)] group-hover:shadow-[0_0_10px_rgba(13,148,136,0.3)] transition-all"></div>
                    <div className="pb-6 w-full">
                      <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">{item.label}</div>
                      <div className="text-sm font-medium text-white bg-transparent p-3 rounded-lg border border-white/10 shadow-sm group-hover:border-[var(--color-x-teal)] transition-colors">
                        {item.value}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="absolute -inset-4 bg-gradient-to-r from-[var(--color-x-cyan)]/5 to-[var(--color-x-teal)]/5 blur-xl -z-10 rounded-3xl"></div>
          </div>
          <div className="order-1 lg:order-2 bg-[#080f23]/50 backdrop-blur-md border border-white/10 shadow-2xl rounded-2xl p-8 md:p-12">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
              Every material risk should be explainable.
            </h2>
            <p className="text-lg text-slate-300 mb-6">
              Xaiote does not simply output "High Risk". It constructs a reconstructable evidence chain.
            </p>
            <p className="text-slate-300 mb-6">
              You can always trace a risk state back to the exact operational event, the original transcript, the AI interpretation, and the specific human confirmation.
            </p>
            <div className="inline-flex items-center gap-2 text-[var(--color-x-teal)] font-semibold border-b border-[var(--color-x-teal)] pb-1">
              Fully explainable architecture
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function WorkOrderImpact() {
  return (
    <section className="py-24 bg-slate-900/50 backdrop-blur-md border-t border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
          Don't stop at the machine. Understand the order.
        </h2>
        <p className="text-lg text-slate-300 max-w-3xl mx-auto mb-16">
          A machine issue does not automatically mean every associated work order is at risk. Xaiote considers allocation, deadlines, remaining quantity, and production buffers.
        </p>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            { title: "Time-Aware Allocation", desc: "Understands exactly when an order needs the affected machine." },
            { title: "Delivery Deadline", desc: "Factors in the actual dispatch commitment, not just internal schedules." },
            { title: "Production Buffer", desc: "Knows if you have enough buffer to absorb a 4-hour breakdown." }
          ].map((feature, i) => (
            <div key={i} className="bg-transparent p-6 rounded-xl shadow-sm border border-white/10 text-left">
              <Activity className="w-8 h-8 text-slate-400 mb-4" />
              <h3 className="font-bold text-white mb-2">{feature.title}</h3>
              <p className="text-sm text-slate-300">{feature.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
