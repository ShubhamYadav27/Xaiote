export const metadata = { title: "Company — Xaiote" };

export default function CompanyPage() {
  return (
    <div className="bg-transparent min-h-screen">
      <section className="bg-slate-950 pt-32 pb-24 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">About Xaiote</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Building the Manufacturing Intelligence OS.</p>
      </section>
      <section className="py-24 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="space-y-12 text-lg text-slate-700">
          <p>
            We believe that factories already possess the data they need to predict and prevent delivery failures. The challenge is that this information is deeply fragmented across structured ERP systems and unstructured shop-floor communication networks like WhatsApp.
          </p>
          <p>
            Xaiote was founded to bridge this gap. We provide a Manufacturing Intelligence layer that connects these disparate signals, enabling organizations to understand what went wrong, why it happened, and exactly which work orders are at risk.
          </p>
          <p>
            We do not ask manufacturers to replace their ERP or MES. We simply ask them to connect the signals they already generate. Our long-term vision is the creation of a comprehensive Manufacturing Intelligence OS that observes, understands, correlates, predicts, recommends, and learns from every operational event on the factory floor.
          </p>
        </div>
      </section>
    </div>
  );
}
