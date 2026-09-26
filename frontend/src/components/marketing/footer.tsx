import Link from "next/link";
import Image from "next/image";

export function Footer() {
  const footerSections = [
    {
      title: "Product",
      links: [
        { name: "Manufacturing Intelligence", href: "/product" },
        { name: "Production Risk", href: "/product#risk" },
        { name: "Root-Cause Intelligence", href: "/product#root-cause" },
        { name: "Work-Order Impact", href: "/product#impact" },
        { name: "Evidence & Investigation", href: "/product#evidence" },
        { name: "Alerts", href: "/product#alerts" },
      ]
    },
    {
      title: "Solutions",
      links: [
        { name: "Owners / MDs", href: "/solutions#owners" },
        { name: "Plant Heads", href: "/solutions#plant-heads" },
        { name: "Production", href: "/solutions#production" },
        { name: "Maintenance", href: "/solutions#maintenance" },
        { name: "Purchase", href: "/solutions#purchase" },
        { name: "Quality", href: "/solutions#quality" },
        { name: "Supervisors", href: "/solutions#supervisors" },
      ]
    },
    {
      title: "Industries",
      links: [
        { name: "Automotive Components", href: "/industries#automotive" },
        { name: "CNC / Precision Machining", href: "/industries#cnc" },
        { name: "Casting", href: "/industries#casting" },
        { name: "Forging", href: "/industries#forging" },
        { name: "Sheet Metal", href: "/industries#sheet-metal" },
        { name: "Fabrication", href: "/industries#fabrication" },
        { name: "Injection Molding", href: "/industries#injection-molding" },
        { name: "Industrial Components", href: "/industries#industrial-components" },
      ]
    },
    {
      title: "Resources",
      links: [
        { name: "How Xaiote Works", href: "/how-it-works" },
        { name: "Security & Governance", href: "/security" },
        { name: "Pilot Guide", href: "/resources#pilot-guide" },
        { name: "Documentation", href: "/resources#docs" },
        { name: "Insights", href: "/resources#insights" },
      ]
    },
    {
      title: "Company",
      links: [
        { name: "About Us", href: "/company" },
        { name: "Contact", href: "/contact" },
        { name: "Careers", href: "/company#careers" },
        { name: "Partners", href: "/company#partners" },
      ]
    }
  ];

  return (
    <footer className="bg-transparent text-slate-300 py-16 border-t border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8 mb-12">
          <div className="col-span-2 lg:col-span-1">
            <div className="mb-6">
              <Image src="/Xaiote(icon).png" alt="Xaiote" width={150} height={48} className="h-10 w-auto" />
            </div>
            <p className="text-sm text-slate-400 mb-6 leading-relaxed">
              Manufacturing Intelligence.<br/>
              Know about production risks before they become delivery failures.
            </p>
          </div>
          {footerSections.map((section) => (
            <div key={section.title}>
              <h3 className="text-sm font-semibold text-white mb-4">{section.title}</h3>
              <ul className="space-y-3">
                {section.links.map((link) => (
                  <li key={link.name}>
                    <Link href={link.href} className="text-sm text-slate-400 hover:text-white transition-colors">
                      {link.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="pt-8 border-t border-slate-800 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-sm text-slate-500">© {new Date().getFullYear()} Xaiote. Manufacturing Intelligence.</p>
          <div className="flex gap-6 text-sm text-slate-500">
            <Link href="/privacy" className="hover:text-white">Privacy</Link>
            <Link href="/terms" className="hover:text-white">Terms</Link>
            <Link href="/security" className="hover:text-white">Security</Link>
            <a href="https://www.linkedin.com/company/xaiote" target="_blank" rel="noopener noreferrer" className="hover:text-white">LinkedIn</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
