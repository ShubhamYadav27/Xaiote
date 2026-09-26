import codecs

content = """
import asyncio
from httpx import AsyncClient
from app.main import app

# ==================== 17. Concurrent Generation ====================
@pytest.mark.asyncio
async def test_concurrent_generation(db_session: AsyncSession, setup_4d):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    
    key = "idem-concurrent-1"
    
    tasks = [
        generate_analysis_for_incident(db_session, inc.id, cid, idempotency_key=key)
        for _ in range(3)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = [r for r in results if not isinstance(r, Exception)]
    
    assert len(successes) > 0
    first_id = successes[0].id
    for s in successes:
        assert s.id == first_id

# ==================== 18. Conflicting Candidates ====================
@pytest.mark.asyncio
async def test_conflicting_candidates(db_session: AsyncSession, setup_4d):
    from app.services.analysis_service import MockAnalysisLLMProvider
    from app.models.analysis import AssessmentEvidenceLink
    
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    ev = setup_4d["ev1"]
    
    original = MockAnalysisLLMProvider.analyze
    
    async def conflicting_analyze(self, events):
        return {
            "candidates": [
                {
                    "category": "MECHANICAL",
                    "role": "PRIMARY",
                    "explanation": "Conflicting test",
                    "supporting_event_ids": [],
                    "conflicting_event_ids": [ev.id],
                    "model_confidence": 0.5,
                }
            ]
        }
        
    MockAnalysisLLMProvider.analyze = conflicting_analyze
    try:
        analysis = await generate_analysis_for_incident(db_session, inc.id, cid, manual_reanalysis=True)
        q = select(AssessmentEvidenceLink).join(RootCauseAssessment).where(
            RootCauseAssessment.analysis_id == analysis.id
        )
        links = (await db_session.execute(q)).scalars().all()
        assert len(links) == 1
        assert links[0].relationship_type == "CONFLICTING"
        assert links[0].event_id == ev.id
        
        async def bad_id_analyze(self, events):
            return {
                "candidates": [
                    {
                        "category": "MECHANICAL",
                        "role": "PRIMARY",
                        "explanation": "Bad ID test",
                        "supporting_event_ids": [],
                        "conflicting_event_ids": ["invalid-id-123"],
                        "model_confidence": 0.5,
                    }
                ]
            }
        MockAnalysisLLMProvider.analyze = bad_id_analyze
        with pytest.raises(ValueError, match="invalid event_id"):
            await generate_analysis_for_incident(db_session, inc.id, cid, manual_reanalysis=True)
    finally:
        MockAnalysisLLMProvider.analyze = original

# ==================== 19. Composite Foreign Key Tests ====================
@pytest.mark.asyncio
async def test_composite_fk_enforcement(db_session: AsyncSession, setup_4d):
    from sqlalchemy.exc import IntegrityError
    
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    
    analysis = await generate_analysis_for_incident(db_session, inc.id, cid, manual_reanalysis=True)
    
    bad_cid = str(uuid.uuid4())
    bad_assessment = RootCauseAssessment(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        company_id=bad_cid,
        status=AssessmentStatus.CANDIDATE,
        category="MECHANICAL",
        role=AssessmentRole.PRIMARY,
        explanation="Test FK",
        provenance="MODEL_DERIVED",
        model_confidence=0.9
    )
    db_session.add(bad_assessment)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

# ==================== 20. Human Confirmation Atomicity ====================
@pytest.mark.asyncio
async def test_human_confirmation_atomicity(db_session: AsyncSession, setup_4d, monkeypatch):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    uid = setup_4d["user"].id
    
    analysis = await generate_analysis_for_incident(db_session, inc.id, cid, manual_reanalysis=True)
    
    assmt = (await db_session.execute(
        select(RootCauseAssessment).where(RootCauseAssessment.analysis_id == analysis.id)
    )).scalars().first()
    
    async def mock_commit():
        raise Exception("Mocked commit failure")
        
    monkeypatch.setattr(db_session, "commit", mock_commit)
    
    with pytest.raises(Exception, match="Mocked commit failure"):
        await confirm_assessment(db_session, assmt.id, cid, uid, expected_revision=1)
        
    monkeypatch.undo()
    
    await db_session.rollback()
    
    await db_session.refresh(assmt)
    assert assmt.status == AssessmentStatus.CANDIDATE
    assert assmt.revision == 1
    
    q_hist = select(AssessmentDecisionHistory).where(AssessmentDecisionHistory.assessment_id == assmt.id)
    histories = (await db_session.execute(q_hist)).scalars().all()
    assert len(histories) == 0

# ==================== 21. RBAC & API Tests ====================
@pytest.mark.asyncio
async def test_api_rbac_generation(setup_4d):
    inc = setup_4d["incident"]
    headers = setup_4d["headers"]
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post(f"/api/v1/incidents/{inc.id}/analysis", headers=headers)
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_api_rbac_confirm(setup_4d, db_session: AsyncSession):
    cid = setup_4d["company"].id
    inc = setup_4d["incident"]
    headers = setup_4d["headers"]
    user = setup_4d["user"]
    
    analysis = await generate_analysis_for_incident(db_session, inc.id, cid, manual_reanalysis=True)
    assmt = (await db_session.execute(
        select(RootCauseAssessment).where(RootCauseAssessment.analysis_id == analysis.id)
    )).scalars().first()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post(f"/api/v1/analysis/assessments/{assmt.id}/confirm", headers=headers, json={"expected_revision": 1})
        assert res.status_code == 403
        
        user.role = "SUPERVISOR"
        db_session.add(user)
        await db_session.commit()
        
        res = await client.post(f"/api/v1/analysis/assessments/{assmt.id}/confirm", headers=headers, json={"expected_revision": 1})
        assert res.status_code == 200

@pytest.mark.asyncio
async def test_api_cross_tenant(setup_4d, db_session: AsyncSession):
    headers = setup_4d["headers"]
    user = setup_4d["user"]
    user.role = "SUPERVISOR"
    db_session.add(user)
    await db_session.commit()
    
    other_inc_id = str(uuid.uuid4())
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post(f"/api/v1/incidents/{other_inc_id}/analysis", headers=headers)
        assert res.status_code in (404, 403)
"""

with codecs.open(r"c:\Xaiote\backend\tests\test_phase_4d_analysis.py", "a", "utf-8") as f:
    f.write(content)
