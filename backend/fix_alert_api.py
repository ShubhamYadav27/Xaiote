import re

with open(r'app/api/routes/alerts.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('alert = await transition_alert_status(', 'await transition_alert_status(')

with open(r'app/api/routes/alerts.py', 'w', encoding='utf-8') as f:
    f.write(t)
