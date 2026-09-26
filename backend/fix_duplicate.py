import re

with open(r'tests/test_phase_4e_3_extended.py', 'r', encoding='utf-8') as f:
    text = f.read()

# find all occurrences of the fixture block:
pattern = r'(@pytest\.fixture\s*async def base_context\(.*?return \{"wo1": wo1\}\s*)'
matches = re.finditer(pattern, text, re.DOTALL)
matches = list(matches)

if len(matches) > 1:
    # remove all except the first
    for match in reversed(matches[1:]):
        text = text[:match.start()] + text[match.end():]
        
with open(r'tests/test_phase_4e_3_extended.py', 'w', encoding='utf-8') as f:
    f.write(text)
