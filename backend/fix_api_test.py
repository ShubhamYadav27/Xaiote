import re

with open(r'tests/test_phase_4e_4_alerts_api.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('from app.core.security import create_access_token', 'import jwt\nfrom app.core.config import settings')
t = t.replace('tok_super = create_access_token({"sub": u_super.email, "company_id": cid, "role": u_super.role})', 'tok_super = jwt.encode({"sub": str(u_super.id)}, settings.JWT_SECRET, algorithm="HS256")')
t = t.replace('tok_view = create_access_token({"sub": u_view.email, "company_id": cid, "role": u_view.role})', 'tok_view = jwt.encode({"sub": str(u_view.id)}, settings.JWT_SECRET, algorithm="HS256")')
t = t.replace('tok_other = create_access_token({"sub": u_other.email, "company_id": c2id, "role": u_other.role})', 'tok_other = jwt.encode({"sub": str(u_other.id)}, settings.JWT_SECRET, algorithm="HS256")')

with open(r'tests/test_phase_4e_4_alerts_api.py', 'w', encoding='utf-8') as f:
    f.write(t)
