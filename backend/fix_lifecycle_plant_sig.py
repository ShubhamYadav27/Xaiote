import re

with open(r'app/services/alert_lifecycle.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('user_plant_id: str = None,\n    new_status: AlertStatus,\n    expected_version: int,',
'new_status: AlertStatus,\n    expected_version: int,\n    user_plant_id: str = None,')

with open(r'app/services/alert_lifecycle.py', 'w', encoding='utf-8') as f:
    f.write(t)
