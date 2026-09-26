import re

content = open('src/components/marketing/home/vision-sections.tsx', encoding='utf-8').read()

content = content.replace(
    'import { ArrowRight, BrainCircuit, Activity, Database, ShieldAlert, Cpu } from "lucide-react";',
    'import { ArrowRight, BrainCircuit, Activity, Database, ShieldAlert, Cpu } from "lucide-react";\nimport { openPilotModal } from "@/components/marketing/PilotModal";'
)

# Button replacement
content = content.replace(
    '''<Link 
            href="/contact" 
            className="inline-flex items-center gap-2 bg-[var(--color-x-teal)] hover:bg-teal-500 text-white font-bold py-4 px-8 rounded-lg shadow-lg hover:shadow-teal-500/25 transition-all"
          >
            Book a Pilot
            <ArrowRight className="w-5 h-5" />
          </Link>''',
    '''<button 
            onClick={openPilotModal}
            className="inline-flex items-center gap-2 bg-[var(--color-x-teal)] hover:bg-teal-500 text-white font-bold py-4 px-8 rounded-lg shadow-lg hover:shadow-teal-500/25 transition-all"
          >
            Book a Pilot
            <ArrowRight className="w-5 h-5" />
          </button>'''
)

open('src/components/marketing/home/vision-sections.tsx', 'w', encoding='utf-8').write(content)
