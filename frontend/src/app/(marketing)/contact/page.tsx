export const metadata = { title: "Book a Pilot — Xaiote" };

export default function ContactPage() {
  return (
    <div className="bg-slate-900/50 backdrop-blur-md min-h-screen">
      <section className="bg-slate-950 pt-32 pb-32 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">See Xaiote in your plant.</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Start with a defined production scope, connect your operational data, and evaluate Xaiote against real production events.</p>
      </section>
      <section className="py-12 px-4 sm:px-6 lg:px-8 -mt-20 relative z-10">
        <div className="max-w-xl mx-auto bg-transparent p-8 md:p-12 rounded-2xl shadow-xl border border-slate-100">
          <h2 className="text-2xl font-bold text-white mb-8">Pilot Inquiry</h2>
          <form className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <label htmlFor="first-name" className="block text-sm font-medium text-slate-700 mb-1">First Name</label>
                <input type="text" id="first-name" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-teal-500 focus:border-teal-500" />
              </div>
              <div>
                <label htmlFor="last-name" className="block text-sm font-medium text-slate-700 mb-1">Last Name</label>
                <input type="text" id="last-name" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-teal-500 focus:border-teal-500" />
              </div>
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">Work Email</label>
              <input type="email" id="email" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-teal-500 focus:border-teal-500" />
            </div>
            <div>
              <label htmlFor="company" className="block text-sm font-medium text-slate-700 mb-1">Company Name</label>
              <input type="text" id="company" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-teal-500 focus:border-teal-500" />
            </div>
            <div>
              <label htmlFor="role" className="block text-sm font-medium text-slate-700 mb-1">Role</label>
              <select id="role" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-teal-500 focus:border-teal-500">
                <option>Owner / MD</option>
                <option>Plant Head</option>
                <option>CTO / IT Leadership</option>
                <option>Production Management</option>
                <option>Other</option>
              </select>
            </div>
            <div>
              <label htmlFor="message" className="block text-sm font-medium text-slate-700 mb-1">Primary production challenge</label>
              <textarea id="message" rows={4} className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-teal-500 focus:border-teal-500"></textarea>
            </div>
            <button type="submit" className="w-full bg-slate-900 text-white font-bold py-3 px-4 rounded-md hover:bg-slate-800 transition-colors">
              Request Pilot Details
            </button>
            <p className="text-xs text-slate-500 text-center mt-4">
              Our team will contact you to discuss pilot scope, baseline data requirements, and evaluation criteria. Indicative pilot pricing will be provided during discovery.
            </p>
          </form>
        </div>
      </section>
    </div>
  );
}
