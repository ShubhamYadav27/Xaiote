export const metadata = { title: "Privacy Policy — Xaiote" };

export default function PrivacyPage() {
  return (
    <div className="bg-transparent min-h-screen">
      <section className="bg-slate-950 pt-32 pb-24 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">Privacy Policy</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Your data, your trust.</p>
      </section>
      <section className="py-24 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="space-y-8 text-lg text-slate-700">
          <p>
            Xaiote takes the privacy and security of your manufacturing data seriously.
            This page will contain our full privacy policy. We are currently preparing the
            formal documentation for publication.
          </p>
          <p>
            For questions about how we handle your data, please contact us at{" "}
            <a href="mailto:privacy@xaiote.com" className="text-teal-600 hover:text-teal-500 underline">
              privacy@xaiote.com
            </a>.
          </p>
        </div>
      </section>
    </div>
  );
}
