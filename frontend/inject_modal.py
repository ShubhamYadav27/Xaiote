import re

content = open('src/app/(marketing)/layout.tsx', encoding='utf-8').read()

content = content.replace(
    'import { AuthProvider } from "@/components/providers/AuthProvider";',
    'import { AuthProvider } from "@/components/providers/AuthProvider";\nimport { PilotModal } from "@/components/marketing/PilotModal";'
)

content = content.replace(
    '<Footer />\n    </div>',
    '<Footer />\n      <PilotModal />\n    </div>'
)

open('src/app/(marketing)/layout.tsx', 'w', encoding='utf-8').write(content)
