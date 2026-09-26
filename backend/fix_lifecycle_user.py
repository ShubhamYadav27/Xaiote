import re

with open(r'tests/test_phase_4e_3_lifecycle.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('from app.models.work_order import WorkOrder', 'from app.models.work_order import WorkOrder\nfrom app.models.user import User')

t = t.replace('db_session.add_all([prod, mach])', '''db_session.add_all([prod, mach])
    user = User(id="user1", company_id="c1_ev_l", email="user1@example.com", hashed_password="pw", is_active=True, role="SUPERVISOR")
    db_session.add(user)''')

with open(r'tests/test_phase_4e_3_lifecycle.py', 'w', encoding='utf-8') as f:
    f.write(t)
