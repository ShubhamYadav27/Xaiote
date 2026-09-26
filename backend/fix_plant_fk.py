import re

with open(r'tests/test_phase_4e_3_plant.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('alert = AlertInstance(\n        id="alert_plant_b",\n        company_id=wo1.company_id,\n        plant_id="plant_b",',
'p2 = Plant(id="plant_b", company_id=wo1.company_id, name="PB", timezone="UTC")\n    db_session.add(p2)\n    await db_session.commit()\n    alert = AlertInstance(\n        id="alert_plant_b",\n        company_id=wo1.company_id,\n        plant_id="plant_b",')

with open(r'tests/test_phase_4e_3_plant.py', 'w', encoding='utf-8') as f:
    f.write(t)
