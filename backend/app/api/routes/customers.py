from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_company
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.masters import Customer
from app.schemas.masters import CustomerCreate, CustomerResponse

router = APIRouter()


@router.post("")
async def create_customer(
    customer_in: CustomerCreate,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    # Check for canonical identity conflict (company_id, external_id)
    if customer_in.external_id:
        existing = await db.execute(
            select(Customer).where(
                Customer.company_id == current_company.id,
                Customer.external_id == customer_in.external_id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=400, detail="Customer with this external_id already exists"
            )

    customer = Customer(
        company_id=current_company.id,
        name=customer_in.name,
        external_id=customer_in.external_id,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return {"data": CustomerResponse.model_validate(customer)}


@router.get("")
async def list_customers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    # Base query for tenant
    base_query = select(Customer).where(Customer.company_id == current_company.id)

    # Total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginated data
    query = base_query.order_by(Customer.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    customers = result.scalars().all()

    return {
        "data": {
            "items": [CustomerResponse.model_validate(c) for c in customers],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }
