import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import AlertEvaluationJob, AlertEvaluationJobStatus, AlertEvaluationJobRetryAudit
from app.models.company import Company
from app.models.plant import Plant
from app.models.user import User

@pytest.fixture
async def setup_api(db_session: AsyncSession):
    import uuid

    def _uid():
        return str(uuid.uuid4())

    cid = _uid()
    c2id = _uid()
    c1 = Company(id=cid, name="Company A")
    c2 = Company(id=c2id, name="Company B")
    p1 = Plant(id=_uid(), company_id=cid, name="Plant A", timezone="UTC")
    
    u_admin = User(id=_uid(), company_id=cid, email="admin@c1", password_hash="pw", full_name="Admin", role="ADMIN", is_active=True)
    u_viewer = User(id=_uid(), company_id=cid, email="viewer@c1", password_hash="pw", full_name="Viewer", role="VIEWER", is_active=True)
    u_admin2 = User(id=_uid(), company_id=c2id, email="admin@c2", password_hash="pw", full_name="Admin2", role="ADMIN", is_active=True)
    
    db_session.add_all([c1, c2, p1, u_admin, u_viewer, u_admin2])
    await db_session.commit()
    
    from app.models.work_order import WorkOrder
    from app.models.masters import Machine, Product
    mac = Machine(id=_uid(), company_id=cid, plant_id=p1.id, name="M")
    prod = Product(id=_uid(), company_id=cid, name="P")
    wo = WorkOrder(id=_uid(), company_id=cid, plant_id=p1.id, order_number="WO1", status="PENDING", machine_id=mac.id, product_id=prod.id, quantity=10)
    
    db_session.add_all([mac, prod, wo])
    await db_session.commit()
    
    return {
        "c1": c1, "c2": c2, "p1": p1, "wo": wo,
        "u_admin": u_admin, "u_viewer": u_viewer, "u_admin2": u_admin2
    }

def get_token(user: User):
    import jwt
    from app.core.config import settings
    return jwt.encode({"sub": str(user.id)}, settings.JWT_SECRET, algorithm="HS256")

@pytest.mark.asyncio
async def test_alert_job_retry_success(async_client: AsyncClient, db_session, setup_api):
    c1 = setup_api["c1"]
    p1 = setup_api["p1"]
    admin = setup_api["u_admin"]
    token = get_token(admin)
    auth_headers_admin = {"Authorization": f"Bearer {token}"}
    
    job = AlertEvaluationJob(
        company_id=c1.id,
        plant_id=p1.id,
        status=AlertEvaluationJobStatus.FAILED.value,
        error_detail="Simulated failure",
        target_work_order_id=setup_api["wo"].id,
        target_incident_id=None
    )
    db_session.add(job)
    await db_session.commit()
    
    # Retry via API
    resp = await async_client.post(
        f"/api/v1/alerts/jobs/{job.id}/retry",
        headers=auth_headers_admin,
        json={"reason": "Config updated"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PENDING"
    
    # Verify DB state
    await db_session.refresh(job)
    assert job.status == "PENDING"
    assert job.error_detail is None
    
    # Verify audit
    audit = (await db_session.execute(select(AlertEvaluationJobRetryAudit).where(AlertEvaluationJobRetryAudit.job_id == job.id))).scalar_one()
    assert audit.previous_state == "FAILED"
    assert audit.new_state == "PENDING"
    assert audit.retry_reason == "Config updated"
    assert audit.original_error == "Simulated failure"

@pytest.mark.asyncio
async def test_alert_job_retry_unauthorized(async_client: AsyncClient, db_session, setup_api):
    # Non-admin user
    c1 = setup_api["c1"]
    p1 = setup_api["p1"]
    viewer = setup_api["u_viewer"]
    token = get_token(viewer)
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    job = AlertEvaluationJob(
        company_id=c1.id,
        plant_id=p1.id,
        status=AlertEvaluationJobStatus.FAILED.value,
        error_detail="Simulated failure",
        target_work_order_id=setup_api["wo"].id,
        target_incident_id=None
    )
    db_session.add(job)
    await db_session.commit()
    
    resp = await async_client.post(
        f"/api/v1/alerts/jobs/{job.id}/retry",
        headers=auth_headers,
        json={"reason": "Config updated"}
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_alert_job_retry_not_failed(async_client: AsyncClient, db_session, setup_api):
    c1 = setup_api["c1"]
    p1 = setup_api["p1"]
    admin = setup_api["u_admin"]
    token = get_token(admin)
    auth_headers_admin = {"Authorization": f"Bearer {token}"}
    
    job = AlertEvaluationJob(
        company_id=c1.id,
        plant_id=p1.id,
        status=AlertEvaluationJobStatus.PROCESSING.value,
        error_detail=None,
        target_work_order_id=setup_api["wo"].id,
        target_incident_id=None
    )
    db_session.add(job)
    await db_session.commit()
    
    resp = await async_client.post(
        f"/api/v1/alerts/jobs/{job.id}/retry",
        headers=auth_headers_admin,
        json={"reason": "Config updated"}
    )
    assert resp.status_code == 400
    assert "Only FAILED jobs can be retried" in resp.json()["detail"]
    
@pytest.mark.asyncio
async def test_alert_job_retry_cross_tenant(async_client: AsyncClient, db_session, setup_api):
    c1 = setup_api["c1"]
    p1 = setup_api["p1"]
    admin2 = setup_api["u_admin2"]
    token = get_token(admin2)
    auth_headers_admin_other_company = {"Authorization": f"Bearer {token}"}
    
    job = AlertEvaluationJob(
        company_id=c1.id,
        plant_id=p1.id,
        status=AlertEvaluationJobStatus.FAILED.value,
        error_detail="Simulated failure",
        target_work_order_id=setup_api["wo"].id,
        target_incident_id=None
    )
    db_session.add(job)
    await db_session.commit()
    
    resp = await async_client.post(
        f"/api/v1/alerts/jobs/{job.id}/retry",
        headers=auth_headers_admin_other_company,
        json={"reason": "Config updated"}
    )
    assert resp.status_code == 404
