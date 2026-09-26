import re

with open(r'app/workers/alert_worker.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('except Exception as e:', 'except Exception as e:  # noqa: BLE001')

with open(r'app/workers/alert_worker.py', 'w', encoding='utf-8') as f:
    f.write(t)
