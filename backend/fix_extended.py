import re

with open(r'tests/test_phase_4e_3_extended.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = "from sqlalchemy.ext.asyncio import AsyncSession\n" + t

with open(r'tests/test_phase_4e_3_extended.py', 'w', encoding='utf-8') as f:
    f.write(t)
