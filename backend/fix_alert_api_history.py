import re

with open(r'app/api/routes/alerts.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = re.sub(r'previous_status: Optional\[str\] = None\n\s*new_status: str\n\s*', '', t)

t = t.replace(
    'action=h.action, previous_status=h.previous_status, new_status=h.new_status,\n            previous_severity=h.previous_severity',
    'action=h.action, previous_severity=h.previous_severity'
)

with open(r'app/api/routes/alerts.py', 'w', encoding='utf-8') as f:
    f.write(t)
