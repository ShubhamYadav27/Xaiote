import re

with open(r'tests/test_phase_4e_3_lifecycle.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('await db_session.commit()\n    return {"wo1": wo1}', '''
    pol = AlertPolicy(id="pol1_ev", company_id="c1_ev_l", version=1, name="Pol1")
    rules = [
        AlertRule(id="rule1_ev_risk", company_id="c1_ev_l", version=1, policy_id="pol1_ev", policy_version=1,
                  alert_family="PRODUCTION_RISK", severity=RiskState.AT_RISK.value, trigger_condition={}, clear_condition={})
    ]
    db_session.add(pol)
    db_session.add_all(rules)
    await db_session.commit()
    return {"wo1": wo1}
''')

with open(r'tests/test_phase_4e_3_lifecycle.py', 'w', encoding='utf-8') as f:
    f.write(t)
