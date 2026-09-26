import pytest
from httpx import AsyncClient
from app.models.alerts import AlertInstance, AlertStatus
from app.models.company import Company
from app.models.plant import Plant
from app.models.masters import Product, Machine
from app.models.work_order import WorkOrder
from app.models.user import User
from app.api.dependencies.auth import get_current_company, get_current_user

# We need to setup auth override for tests. 
# Or we can just use the standard test fixtures if they mock auth.
# Let's inspect test_phase_4c_incident.py to see how they do it.
