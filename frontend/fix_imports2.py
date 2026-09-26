import re

for filename in ['src/components/marketing/home/hero-sections.tsx', 'src/components/marketing/home/vision-sections.tsx']:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'import { openPilotModal }' not in content:
        content = content.replace(
            'import Link from "next/link";',
            'import Link from "next/link";\nimport { openPilotModal } from "@/components/marketing/PilotModal";'
        )
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
