import re

files = ['frontend/src/app/(dashboard)/events/page.tsx', 'frontend/src/app/(dashboard)/events/[id]/page.tsx']
for f in files:
    with open(f, 'r') as file:
        content = file.read()
    
    # We will just fix the specific fetchApi lines by regex
    content = re.sub(r'fetchApi\(\\\/events/\?\\\$\{(.*?)\}\\\\\\)', r'fetchApi(/events/?)', content)
    content = re.sub(r'fetchApi\(\\\/events/\\\$\{(.*?)\}\\\\\\)', r'fetchApi(/events/)', content)
    content = re.sub(r'fetchApi\(\\\/events/\\\$\{(.*?)\}/revisions\\\\\\\)', r'fetchApi(/events//revisions)', content)
    
    with open(f, 'w') as file:
        file.write(content)
