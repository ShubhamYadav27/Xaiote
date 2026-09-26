import re

with open(r'tests/test_phase_4e_3_lifecycle.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('hashed_password="pw"', 'password_hash="pw"')

with open(r'tests/test_phase_4e_3_lifecycle.py', 'w', encoding='utf-8') as f:
    f.write(t)
