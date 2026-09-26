import re

with open(r'app/services/alert_lifecycle.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('def transition_alert_status(\n    db: AsyncSession,\n    alert_id: str,\n    company_id: str,\n    user_id: str,',
'def transition_alert_status(\n    db: AsyncSession,\n    alert_id: str,\n    company_id: str,\n    user_id: str,\n    user_plant_id: str = None,')

t = t.replace('''
    stmt = select(AlertInstance).where(
        AlertInstance.id == alert_id,
        AlertInstance.company_id == company_id
    ).with_for_update()''',
'''
    stmt = select(AlertInstance).where(
        AlertInstance.id == alert_id,
        AlertInstance.company_id == company_id
    )
    if user_plant_id:
        stmt = stmt.where(AlertInstance.plant_id == user_plant_id)
    stmt = stmt.with_for_update()''')

with open(r'app/services/alert_lifecycle.py', 'w', encoding='utf-8') as f:
    f.write(t)
