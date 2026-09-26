export const metadata = { title: "How It Works — Xaiote" };

export default function HowItWorksPage() {
  return (
    <div className="bg-transparent">
      <section className="bg-slate-950 pt-32 pb-24 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">How Xaiote Works</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">The intelligence pipeline from factory signal to management action.</p>
      </section>
      <section className="py-24 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="space-y-12">
          {[
            { step: "01", title: "Capture", desc: "Xaiote ingests structured production data (via CSV/Excel) and unstructured shop-floor communication (via official WhatsApp Business)." },
            { step: "02", title: "Understand", desc: "Audio is transcribed and AI extracts entities like machines, parts, and downtime estimates." },
            { step: "03", title: "Validate", desc: "Extracted data is validated against the known factory context." },
            { step: "04", title: "Correlate", desc: "The operational event is mapped to specific work orders and commitments." },
            { step: "05", title: "Assess & Alert", desc: "Deterministic business logic evaluates the delivery risk and alerts the right people based on severity." }
          ].map((s) => (
            <div key={s.step} className="flex gap-6 items-start border-b border-slate-100 pb-12">
              <div className="text-4xl font-bold text-teal-600/20">{s.step}</div>
              <div>
                <h3 className="text-2xl font-bold text-white mb-3">{s.title}</h3>
                <p className="text-lg text-slate-400">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
