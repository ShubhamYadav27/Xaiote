export const metadata = { title: "Security, Trust & Governance — Xaiote" };

export default function SecurityPage() {
  return (
    <div className="bg-transparent">
      <section className="bg-slate-950 pt-32 pb-24 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">Security, Trust & Governance</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Built for sensitive manufacturing operations. Security is designed into the architecture from the beginning.</p>
      </section>
      <section className="py-24 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="space-y-16">
          <div>
            <h2 className="text-3xl font-bold text-white mb-6">Trust Architecture</h2>
            <div className="bg-slate-900/50 backdrop-blur-md p-6 rounded-xl border border-white/10 text-slate-700 font-medium text-center flex flex-wrap justify-center items-center gap-2">
              <span className="bg-transparent px-3 py-1 rounded shadow-sm border border-white/10">Official WhatsApp Business</span>
              <span>→</span>
              <span className="bg-transparent px-3 py-1 rounded shadow-sm border border-white/10">Verified Webhook</span>
              <span>→</span>
              <span className="bg-transparent px-3 py-1 rounded shadow-sm border border-white/10">Controlled Processing</span>
              <span>→</span>
              <span className="bg-transparent px-3 py-1 rounded shadow-sm border border-white/10">STT / AI</span>
              <span>→</span>
              <span className="bg-transparent px-3 py-1 rounded shadow-sm border border-white/10">Validation</span>
              <span>→</span>
              <span className="bg-transparent px-3 py-1 rounded shadow-sm border border-white/10">Entity Resolution</span>
              <span>→</span>
              <span className="bg-teal-950/30 text-teal-400 px-3 py-1 rounded shadow-sm border border-teal-900/50">Xaiote</span>
            </div>
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white mb-6">Core Principles</h2>
            <div className="grid md:grid-cols-2 gap-8">
              <div className="bg-transparent p-6 rounded-xl border border-white/10">
                <h3 className="font-bold text-white mb-2">Tenant Isolation</h3>
                <p className="text-sm text-slate-400">Strict separation of data between tenants. No mixing of production schedules or communication data.</p>
              </div>
              <div className="bg-transparent p-6 rounded-xl border border-white/10">
                <h3 className="font-bold text-white mb-2">RBAC & Least Privilege</h3>
                <p className="text-sm text-slate-400">Access to evidence, logs, and sensitive work order details is restricted by role.</p>
              </div>
              <div className="bg-transparent p-6 rounded-xl border border-white/10">
                <h3 className="font-bold text-white mb-2">Audit Logging</h3>
                <p className="text-sm text-slate-400">Evidence access, system actions, and human confirmations are securely logged.</p>
              </div>
              <div className="bg-transparent p-6 rounded-xl border border-white/10">
                <h3 className="font-bold text-white mb-2">Retention Controls</h3>
                <p className="text-sm text-slate-400">Configurable retention for audio files, transcripts, and operational history.</p>
              </div>
            </div>
          </div>
          <div className="bg-red-950/20 backdrop-blur-md p-8 rounded-xl border border-red-900/30">
            <h2 className="text-2xl font-bold text-red-300 mb-4">"AI does not create facts."</h2>
            <p className="text-red-400">Our models are strictly confined to extraction, classification, and summarization. We use deterministic business logic for risk and impact calculation. We never allow AI to invent downtime, change customer commitments, or alter critical production states autonomously.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
