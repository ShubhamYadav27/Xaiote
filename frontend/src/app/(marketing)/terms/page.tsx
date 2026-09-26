export const metadata = { title: "Terms of Service — Xaiote" };

export default function TermsPage() {
  return (
    <div className="bg-transparent min-h-screen">
      <section className="bg-slate-950 pt-32 pb-24 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">Terms of Service</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Fair and transparent terms.</p>
      </section>
      <section className="py-24 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="space-y-8 text-lg text-slate-700">
          <p>
            Xaiote provides Manufacturing Intelligence services under terms that protect
            both your business and ours. Our formal Terms of Service are currently being
            finalized for publication.
          </p>
          <p>
            For questions, please contact us at{" "}
            <a href="mailto:legal@xaiote.com" className="text-teal-600 hover:text-teal-500 underline">
              legal@xaiote.com
            </a>.
          </p>
        </div>
      </section>
    </div>
  );
}
