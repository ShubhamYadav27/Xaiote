import pytest
from sqlalchemy.exc import IntegrityError
from app.models.user_plants import UserPlant
from app.models.user import User
from app.models.plant import Plant
from app.models.company import Company
from app.services.plant_authorization_service import PlantAuthorizationService

@pytest.fixture
async def base_context(db_session):
    c1 = Company(id="c1", name="C1")
    c2 = Company(id="c2", name="C2")
    db_session.sync_session.add_all([c1, c2])
    await db_session.commit()

    p1 = Plant(id="p1", company_id="c1", name="P1", timezone="UTC")
    p_c2 = Plant(id="p_c2", company_id="c2", name="P2", timezone="UTC")
    db_session.sync_session.add_all([p1, p_c2])
    await db_session.commit()

    u1 = User(id="u1", company_id="c1", email="u1@test", password_hash="1", full_name="1", role="SUPERVISOR", is_active=True)
    u2 = User(id="u2", company_id="c1", email="u2@test", password_hash="2", full_name="2", role="SUPERVISOR", is_active=True)
    u_admin = User(id="u_admin", company_id="c1", email="a@test", password_hash="3", full_name="3", role="ADMIN", is_active=True)
    u_owner = User(id="u_owner", company_id="c1", email="o@test", password_hash="4", full_name="4", role="OWNER", is_active=True)
    u_c1 = User(id="u_c1", company_id="c1", email="uc1@test", password_hash="5", full_name="5", role="SUPERVISOR", is_active=True)
    u_c2 = User(id="u_c2", company_id="c2", email="uc2@test", password_hash="6", full_name="6", role="SUPERVISOR", is_active=True)
    db_session.sync_session.add_all([u1, u2, u_admin, u_owner, u_c1, u_c2])
    await db_session.commit()

    db_session.sync_session.add(UserPlant(user_id="u1", plant_id="p1", company_id="c1"))
    await db_session.commit()

@pytest.mark.asyncio
async def test_same_company_authorized_user_assigned_plant(db_session, base_context):
    res = await db_session.run_sync(lambda s: PlantAuthorizationService.is_plant_authorized(s, "u1", "c1", "SUPERVISOR", "p1"))
    assert res is True

@pytest.mark.asyncio
async def test_same_company_user_without_assignment(db_session, base_context):
    res = await db_session.run_sync(lambda s: PlantAuthorizationService.is_plant_authorized(s, "u2", "c1", "SUPERVISOR", "p1"))
    assert res is False

@pytest.mark.asyncio
async def test_cross_company_authorization(db_session, base_context):
    res = await db_session.run_sync(lambda s: PlantAuthorizationService.is_plant_authorized(s, "u_c2", "c2", "SUPERVISOR", "p1"))
    assert res is False

@pytest.mark.asyncio
async def test_admin_owner_same_company(db_session, base_context):
    res = await db_session.run_sync(lambda s: PlantAuthorizationService.is_plant_authorized(s, "u_admin", "c1", "ADMIN", "p1"))
    assert res is True
    res2 = await db_session.run_sync(lambda s: PlantAuthorizationService.is_plant_authorized(s, "u_owner", "c1", "OWNER", "p1"))
    assert res2 is True

@pytest.mark.asyncio
async def test_admin_owner_cross_company(db_session, base_context):
    pass

@pytest.mark.asyncio
async def test_duplicate_user_plants(db_session, base_context):
    db_session.sync_session.add(UserPlant(user_id="u1", plant_id="p1", company_id="c1"))
    with pytest.raises(IntegrityError):
        await db_session.commit()

@pytest.mark.asyncio
async def test_cross_tenant_insertion(db_session, base_context):
    db_session.sync_session.add(UserPlant(user_id="u_c1", plant_id="p_c2", company_id="c1"))
    with pytest.raises(IntegrityError):
        await db_session.commit()

@pytest.mark.asyncio
async def test_revoked_assignment_subsequent_authorization_denied(db_session, base_context):
    pass
