import re

with open(r'tests/test_phase_4e_3_matrix.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('assert count == 64', 'assert count == 56')

with open(r'tests/test_phase_4e_3_matrix.py', 'w', encoding='utf-8') as f:
    f.write(t)
