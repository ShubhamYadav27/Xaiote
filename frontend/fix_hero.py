import re
with open('src/components/marketing/home/hero-sections.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'<Link href="/contact" className="inline-flex justify-center items-center gap-2 bg-\[var\(--color-x-teal\)\].*?Book a Pilot\s*<ArrowRight className="w-4 h-4" />\s*</Link>',
    r'<button onClick={openPilotModal} className="inline-flex justify-center items-center gap-2 bg-[var(--color-x-teal)] hover:bg-teal-500 text-white px-6 py-3 rounded-md font-semibold transition-colors shadow-lg w-full sm:w-auto">Book a Pilot<ArrowRight className="w-4 h-4" /></button>',
    content,
    flags=re.DOTALL
)
with open('src/components/marketing/home/hero-sections.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
