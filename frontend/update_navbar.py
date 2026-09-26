import re

content = open('src/components/marketing/navbar.tsx', encoding='utf-8').read()

content = content.replace(
    'import { useAuth } from "@/components/providers/AuthProvider";',
    'import { useAuth } from "@/components/providers/AuthProvider";\nimport { openPilotModal } from "@/components/marketing/PilotModal";'
)

# Desktop button
content = content.replace(
    '''<Link 
                href="/contact" 
                className="bg-[var(--color-x-teal)] hover:bg-teal-500 text-white px-4 py-2 rounded-md text-sm font-semibold transition-colors flex items-center gap-2 shadow-lg"
              >
                Book a Pilot
                <ArrowRight className="w-4 h-4" />
              </Link>''',
    '''<button 
                onClick={openPilotModal}
                className="bg-[var(--color-x-teal)] hover:bg-teal-500 text-white px-4 py-2 rounded-md text-sm font-semibold transition-colors flex items-center gap-2 shadow-lg"
              >
                Book a Pilot
                <ArrowRight className="w-4 h-4" />
              </button>'''
)

# Mobile button
content = content.replace(
    '''<Link href="/contact" className="text-base font-semibold text-white bg-[var(--color-x-teal)] hover:bg-teal-500 transition-colors px-4 py-2 rounded-lg text-center shadow-lg">Book a Pilot</Link>''',
    '''<button onClick={(e) => { setIsOpen(false); openPilotModal(e); }} className="text-base font-semibold text-white bg-[var(--color-x-teal)] hover:bg-teal-500 transition-colors px-4 py-2 rounded-lg text-center shadow-lg w-full">Book a Pilot</button>'''
)

open('src/components/marketing/navbar.tsx', 'w', encoding='utf-8').write(content)
