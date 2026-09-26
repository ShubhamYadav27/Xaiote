export const metadata = { title: "Resources — Xaiote" };

export default function ResourcesPage() {
  return (
    <div className="bg-transparent min-h-screen">
      <section className="bg-slate-950 pt-32 pb-24 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">Resources</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Guides, documentation, and operational insights for Manufacturing Intelligence.</p>
      </section>
      <section className="py-24 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-2 gap-8">
          <div id="pilot-guide" className="p-8 border border-white/10 rounded-2xl hover:border-teal-500 transition-colors">
            <div className="w-12 h-12 bg-teal-950/30 rounded-lg flex items-center justify-center text-teal-400 font-bold mb-6">01</div>
            <h2 className="text-2xl font-bold text-white mb-4">Pilot Evaluation Guide</h2>
            <p className="text-slate-400 mb-6">Learn how to structure a proof-of-value pilot, connect your data, and measure the operational value of earlier visibility.</p>
            <a href="/contact" className="text-teal-400 font-semibold hover:text-teal-700">Request the Guide →</a>
          </div>
          <div id="docs" className="p-8 border border-white/10 rounded-2xl hover:border-teal-500 transition-colors">
            <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center text-slate-400 font-bold mb-6">02</div>
            <h2 className="text-2xl font-bold text-white mb-4">Product Documentation</h2>
            <p className="text-slate-400 mb-6">Technical specifications for CSV structures, WhatsApp sender mapping, and role-based access configurations.</p>
            <span className="text-slate-400 font-medium">Available for current pilots</span>
          </div>
        </div>
      </section>
    </div>
  );
}
