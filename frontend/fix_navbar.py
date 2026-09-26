import re
with open('src/components/marketing/navbar.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'<Link\s+href="/contact"\s+className="bg-\[var\(--color-x-teal\)\].*?Book a Pilot\s*<ArrowRight className="w-4 h-4" />\s*</Link>',
    r'<button onClick={openPilotModal} className="bg-[var(--color-x-teal)] hover:bg-teal-500 text-white px-4 py-2 rounded-md text-sm font-semibold transition-colors flex items-center gap-2 shadow-lg">Book a Pilot<ArrowRight className="w-4 h-4" /></button>',
    content,
    flags=re.DOTALL
)
with open('src/components/marketing/navbar.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
