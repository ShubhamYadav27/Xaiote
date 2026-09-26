import glob
import re

migration_files = glob.glob(r'C:\Xaiote\backend\alembic\versions\*_phase_4e_3_eval_job.py')
latest = sorted(migration_files)[-1]

with open(latest, 'r', encoding='utf-8') as f:
    t = f.read()

lines = t.split('\n')
new_lines = []
skip = False
for line in lines:
    if line.strip().startswith("op.alter_column("):
        skip = True
    if not skip:
        new_lines.append(line)
    if skip and line.strip().endswith(")"):
        if "existing_nullable" in line or "existing_server_default" in line:
            skip = False

with open(latest, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))
