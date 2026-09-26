import re

with open(r'app/services/alert_lifecycle.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('user_plant_id: str = None', 'user_plant_id: str | None = None')

with open(r'app/services/alert_lifecycle.py', 'w', encoding='utf-8') as f:
    f.write(t)
