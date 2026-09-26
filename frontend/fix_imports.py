import codecs
import re
file_path = 'src/components/marketing/PilotModal.tsx'
with codecs.open(file_path, 'r', 'utf-8') as f:
    content = f.read()

# Remove duplicate imports
content = re.sub(r'import \{ useState, useEffect \} from \'react\';\nimport \{ createPortal \} from \'react-dom\';\n', '', content, count=1)

# Ensure only one isOpen declaration
content = re.sub(r'const \[isOpen, setIsOpen\] = useState\(false\);\n  const \[mounted, setMounted\] = useState\(false\);\n', '', content, count=1)

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(content)
