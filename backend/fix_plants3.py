import os
for root, _, files in os.walk('backend/tests'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            content = content.replace('name=\"Plant A\")', 'name=\"Plant A\", timezone=\"UTC\")')
            content = content.replace('name=\"Plant 2\")', 'name=\"Plant 2\", timezone=\"UTC\")')
            content = content.replace('name=\"Plant 1\")', 'name=\"Plant 1\", timezone=\"UTC\")')
            content = content.replace('name=\"Plant 4E\")', 'name=\"Plant 4E\", timezone=\"UTC\")')
            content = content.replace('name=\"Plant 4D\")', 'name=\"Plant 4D\", timezone=\"UTC\")')
            content = content.replace('name=\"Other Plant\")', 'name=\"Other Plant\", timezone=\"UTC\")')
            content = content.replace('name=\"Plant A2\")', 'name=\"Plant A2\", timezone=\"UTC\")')
            content = content.replace('name=\"P1\")', 'name=\"P1\", timezone=\"UTC\")')
            content = content.replace('name=\"P2\")', 'name=\"P2\", timezone=\"UTC\")')
            content = content.replace('name=\"PB\")', 'name=\"PB\", timezone=\"UTC\")')
            with open(path, 'w', encoding='utf-8') as file:
                file.write(content)
