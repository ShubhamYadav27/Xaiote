import re

with open(r'tests/test_phase_4e_2_alerts.py', 'r', encoding='utf-8') as f:
    t = f.read()

new_test = '''
@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()

'''

with open(r'tests/test_phase_4e_2_alerts.py', 'w', encoding='utf-8') as f:
    f.write(t + "\n" + new_test)
