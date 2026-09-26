export const metadata = { title: "Product — Xaiote Manufacturing Intelligence" };

export default function ProductPage() {
  return (
    <div className="bg-transparent">
      <section className="bg-slate-950 pt-32 pb-24 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">Manufacturing Intelligence</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Production Risk & Root-Cause Intelligence designed for the reality of modern factories.</p>
      </section>
      <section className="py-24 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="space-y-24">
          <div id="risk">
            <h2 className="text-3xl font-bold text-white mb-4">Production Risk</h2>
            <p className="text-lg text-slate-400 mb-6">Connect unstructured signals from the shop floor with your structured ERP data to automatically detect and classify production risks before they affect delivery.</p>
          </div>
          <div id="root-cause">
            <h2 className="text-3xl font-bold text-white mb-4">Root-Cause Intelligence</h2>
            <p className="text-lg text-slate-400 mb-6">Instantly understand why a disruption occurred. Xaiote extracts and maps the exact machine failure, material shortage, or quality issue causing the delay.</p>
          </div>
          <div id="impact">
            <h2 className="text-3xl font-bold text-white mb-4">Work-Order Impact</h2>
            <p className="text-lg text-slate-400 mb-6">Not all downtime affects delivery. Xaiote evaluates order allocation, deadlines, and production buffer to deterministically calculate actual customer impact.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
