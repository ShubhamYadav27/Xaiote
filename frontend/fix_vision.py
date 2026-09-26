import re
with open('src/components/marketing/home/vision-sections.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'<Link href="/contact" className="inline-flex justify-center items-center gap-2 bg-\[var\(--color-x-teal\)\].*?Book a Pilot\s*<ArrowRight className="w-5 h-5" />\s*</Link>',
    r'<button onClick={openPilotModal} className="inline-flex justify-center items-center gap-2 bg-[var(--color-x-teal)] hover:bg-teal-500 text-white shadow-lg px-8 py-4 rounded-md font-bold text-lg transition-colors w-full sm:w-auto">Book a Pilot<ArrowRight className="w-5 h-5" /></button>',
    content,
    flags=re.DOTALL
)
with open('src/components/marketing/home/vision-sections.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
