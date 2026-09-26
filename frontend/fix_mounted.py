import codecs
import re
file_path = 'src/components/marketing/PilotModal.tsx'
with codecs.open(file_path, 'r', 'utf-8') as f:
    content = f.read()

# Add mounted state back right after isOpen
content = content.replace('const [isOpen, setIsOpen] = useState(false);', 'const [isOpen, setIsOpen] = useState(false);\n  const [mounted, setMounted] = useState(false);')

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(content)
