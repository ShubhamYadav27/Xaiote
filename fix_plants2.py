import os, re
for root, _, files in os.walk('backend/tests'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            # First, revert the broken replacements
            content = content.replace('(, timezone=\"UTC\")', '()')
            
            # Now properly add timezone="UTC" at the end of the Plant(...) instantiation if not there
            # A safe way is to find name="something" and append it there, IF inside a Plant(...)
            def replacer(match):
                if 'timezone=' not in match.group(0):
                    return match.group(1) + ', timezone=\"UTC\"' + match.group(2)
                return match.group(0)
                
            new_content = re.sub(r'(Plant\([^)]*?name=[\"\'][^\"\']*[\"\')]+)(?=\))', replacer, content)
            # Actually, the above might be tricky. Let's just fix the broken uuid4() first.
            new_content = content.replace(', timezone="UTC"', '')
            new_content = re.sub(r'(Plant\([^)]*?name=[\"\'][^\"\']*[\"\'])\s*\)', r'\1, timezone="UTC")', new_content)
            
            with open(path, 'w', encoding='utf-8') as file:
                file.write(new_content)
            print(f'Fixed {path}')
