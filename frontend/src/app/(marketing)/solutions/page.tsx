export const metadata = { title: "Solutions — Xaiote" };

export default function SolutionsPage() {
  const roles = [
    { id: "owners", name: "Owners & MDs", need: "Visibility into production and delivery risk", value: "High-level risk aggregation, critical orders overview, and top root causes." },
    { id: "plant-heads", name: "Plant Heads", need: "Know what requires intervention", value: "At-risk orders, critical issues, root cause investigation, and actionable alerts." },
    { id: "production", name: "Production", need: "Manage schedule and constraints", value: "Order impact, allocation tracking, timeline risk states." },
    { id: "maintenance", name: "Maintenance", need: "Respond to machine issues", value: "Machine incident logging, affected orders visibility, recovery context." },
    { id: "purchase", name: "Purchase", need: "Resolve vendor/material constraints", value: "Vendor/material events tracking, affected production visibility." },
    { id: "quality", name: "Quality", need: "Control rejection/rework", value: "Quality incidents, causes, affected work orders." },
    { id: "supervisors", name: "Supervisors", need: "Report issues quickly", value: "Frictionless WhatsApp-based workflow with minimal change management." },
  ];

  return (
    <div className="bg-transparent">
      <section className="bg-slate-950 pt-32 pb-24 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">Solutions by Role</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Intelligence tailored to every function in the factory.</p>
      </section>
      <section className="py-24 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="space-y-16">
          {roles.map((role) => (
            <div key={role.id} id={role.id} className="bg-slate-900/50 backdrop-blur-md p-8 rounded-2xl border border-white/10">
              <h2 className="text-2xl font-bold text-white mb-6">{role.name}</h2>
              <div className="grid md:grid-cols-2 gap-8">
                <div>
                  <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">The Need</h3>
                  <p className="text-slate-700">{role.need}</p>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">Xaiote Delivers</h3>
                  <p className="text-teal-700 font-medium">{role.value}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
