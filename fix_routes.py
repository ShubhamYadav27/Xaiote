import codecs

file_path = r"c:\Xaiote\backend\tests\test_phase_4d_analysis.py"
with codecs.open(file_path, "r", "utf-8") as f:
    text = f.read()

idx = text.find('# ==================== 21. RBAC & API Tests ====================')
if idx != -1:
    text = text[:idx] + """# ==================== 21. RBAC & API Tests ====================
@pytest.mark.asyncio
async def test_api_rbac_generation(setup_4d, async_client):
    inc = setup_4d["incident"]
    headers = setup_4d["headers"]
    
    res = await async_client.post(f"/api/v1/analysis/incidents/{inc.id}/generate", json={"incident_id": inc.id}, headers=headers)
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_api_rbac_confirm(setup_4d, db_session: AsyncSession, async_client):
    cid = setup_4d["company"].id
    inc = setup_4d["incident"]
    headers = setup_4d["headers"]
    user = setup_4d["user"]
    
    analysis = await generate_analysis_for_incident(db_session, inc.id, cid, manual_reanalysis=True)
    assmt = (await db_session.execute(
        select(RootCauseAssessment).where(RootCauseAssessment.analysis_id == analysis.id)
    )).scalars().first()
    
    res = await async_client.post(f"/api/v1/analysis/{analysis.id}/assessments/{assmt.id}/confirm", json={"expected_revision": 1}, headers=headers)
    assert res.status_code == 403
    
    user.role = "SUPERVISOR"
    db_session.add(user)
    await db_session.commit()
    
    res = await async_client.post(f"/api/v1/analysis/{analysis.id}/assessments/{assmt.id}/confirm", json={"expected_revision": 1}, headers=headers)
    assert res.status_code == 200

@pytest.mark.asyncio
async def test_api_cross_tenant(setup_4d, db_session: AsyncSession, async_client):
    headers = setup_4d["headers"]
    user = setup_4d["user"]
    user.role = "SUPERVISOR"
    db_session.add(user)
    await db_session.commit()
    
    import uuid
    other_inc_id = str(uuid.uuid4())
    res = await async_client.post(f"/api/v1/analysis/incidents/{other_inc_id}/generate", json={"incident_id": other_inc_id}, headers=headers)
    assert res.status_code in (404, 403)
"""

with codecs.open(file_path, "w", "utf-8") as f:
    f.write(text)
