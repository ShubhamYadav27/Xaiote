import os
for root, _, files in os.walk('backend/tests'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            lines = content.split('\n')
            new_lines = []
            changed = False
            for line in lines:
                if 'Plant(' in line and 'name=' in line and 'timezone' not in line:
                    line = line.replace(')', ', timezone=\"UTC\")', 1)
                    changed = True
                new_lines.append(line)
            if changed:
                with open(path, 'w', encoding='utf-8') as file:
                    file.write('\n'.join(new_lines))
                print(f'Updated {path}')
