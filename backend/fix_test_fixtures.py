import re

with open(r'tests/test_phase_4e_3_worker.py', 'r', encoding='utf-8') as f:
    t = f.read()
t = t.replace('from app.models.work_order import WorkOrder', 'from app.models.work_order import WorkOrder\nfrom app.models.masters import Product, Machine')
t = t.replace('await db_session.commit()\n\n    wo1 = WorkOrder(', 
'''await db_session.commit()
    prod = Product(id="prod1_ev_w", company_id="c1_ev_w", name="P")
    mach = Machine(id="mach1_ev_w", company_id="c1_ev_w", plant_id="p1_ev_w", name="M")
    db_session.add_all([prod, mach])
    await db_session.commit()

    wo1 = WorkOrder(product_id="prod1_ev_w", machine_id="mach1_ev_w", quantity=100.0, ''')
with open(r'tests/test_phase_4e_3_worker.py', 'w', encoding='utf-8') as f:
    f.write(t)


with open(r'tests/test_phase_4e_3_lifecycle.py', 'r', encoding='utf-8') as f:
    t2 = f.read()
t2 = t2.replace('from app.models.work_order import WorkOrder', 'from app.models.work_order import WorkOrder\nfrom app.models.masters import Product, Machine')
t2 = t2.replace('await db_session.commit()\n\n    wo1 = WorkOrder(', 
'''await db_session.commit()
    prod = Product(id="prod1_ev_l", company_id="c1_ev_l", name="P")
    mach = Machine(id="mach1_ev_l", company_id="c1_ev_l", plant_id="p1_ev_l", name="M")
    db_session.add_all([prod, mach])
    await db_session.commit()

    wo1 = WorkOrder(product_id="prod1_ev_l", machine_id="mach1_ev_l", quantity=100.0, ''')
with open(r'tests/test_phase_4e_3_lifecycle.py', 'w', encoding='utf-8') as f:
    f.write(t2)


with open(r'tests/test_phase_4e_3_evaluator.py', 'r', encoding='utf-8') as f:
    t3 = f.read()
t3 = t3.replace('from app.models.work_order import WorkOrder', 'from app.models.work_order import WorkOrder\nfrom app.models.masters import Product, Machine')
t3 = t3.replace('await db_session.commit()\n\n    wo1 = WorkOrder(', 
'''await db_session.commit()
    prod = Product(id="prod1_ev", company_id="c1_ev", name="P")
    mach = Machine(id="mach1_ev", company_id="c1_ev", plant_id="p1_ev", name="M")
    db_session.add_all([prod, mach])
    await db_session.commit()

    wo1 = WorkOrder(product_id="prod1_ev", machine_id="mach1_ev", quantity=100.0, ''')
with open(r'tests/test_phase_4e_3_evaluator.py', 'w', encoding='utf-8') as f:
    f.write(t3)
