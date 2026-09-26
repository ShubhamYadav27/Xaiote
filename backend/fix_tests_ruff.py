import os
for f in os.listdir('tests'):
    if f.startswith('test_phase_4e_3'):
        path = os.path.join('tests', f)
        with open(path, 'r', encoding='utf-8') as file:
            t = file.read()
        t = t.replace('list(RiskTriggerType)[0]', 'next(iter(RiskTriggerType))')
        with open(path, 'w', encoding='utf-8') as file:
            file.write(t)
