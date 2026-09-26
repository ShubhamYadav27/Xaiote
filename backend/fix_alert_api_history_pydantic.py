import re

with open(r'app/api/routes/alerts.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('new_severity: Optional[str] = None', 'new_severity: str | None = None')

with open(r'app/api/routes/alerts.py', 'w', encoding='utf-8') as f:
    f.write(t)
