import re

content = open('src/components/marketing/home/hero-sections.tsx', encoding='utf-8').read()

content = content.replace(
    'import { ArrowRight, ChevronRight, Play } from "lucide-react";',
    'import { ArrowRight, ChevronRight, Play } from "lucide-react";\nimport { openPilotModal } from "@/components/marketing/PilotModal";'
)

# Button replacement
content = content.replace(
    '''<Link 
                href="/contact" 
                className="bg-[var(--color-x-teal)] hover:bg-teal-500 text-white px-6 py-3 rounded-md font-bold text-lg transition-colors flex items-center justify-center gap-2 shadow-lg"
              >
                Book a Pilot
                <ArrowRight className="w-4 h-4" />
              </Link>''',
    '''<button 
                onClick={openPilotModal}
                className="bg-[var(--color-x-teal)] hover:bg-teal-500 text-white px-6 py-3 rounded-md font-bold text-lg transition-colors flex items-center justify-center gap-2 shadow-lg w-full sm:w-auto"
              >
                Book a Pilot
                <ArrowRight className="w-4 h-4" />
              </button>'''
)

open('src/components/marketing/home/hero-sections.tsx', 'w', encoding='utf-8').write(content)
