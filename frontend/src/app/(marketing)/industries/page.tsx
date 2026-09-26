export const metadata = { title: "Industries — Xaiote" };

export default function IndustriesPage() {
  const industries = [
    { id: "automotive", name: "Automotive Components" },
    { id: "cnc", name: "CNC / Precision Machining" },
    { id: "casting", name: "Casting" },
    { id: "forging", name: "Forging" },
    { id: "sheet-metal", name: "Sheet Metal" },
    { id: "fabrication", name: "Fabrication" },
    { id: "injection-molding", name: "Injection Molding" },
    { id: "industrial-components", name: "Industrial Components" },
    { id: "electronics", name: "Electrical / Electronics Components" },
    { id: "engineering", name: "Engineering Manufacturing" },
    { id: "equipment", name: "Industrial Equipment & Parts" }
  ];

  return (
    <div className="bg-transparent min-h-screen">
      <section className="bg-slate-950 pt-32 pb-24 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">Industries</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Designed initially for mid-market manufacturing environments.</p>
      </section>
      <section className="py-24 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-2 gap-6">
          {industries.map((ind) => (
            <div key={ind.id} id={ind.id} className="p-6 border border-white/10 rounded-xl hover:shadow-md transition-shadow">
              <h2 className="text-xl font-bold text-white">{ind.name}</h2>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
