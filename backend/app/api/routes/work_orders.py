from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_company
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.masters import Customer, Machine, Product
from app.models.plant import Plant
from app.models.work_order import WorkOrder, WorkOrderStatus
from app.schemas.work_orders import WorkOrderCreate, WorkOrderResponse

router = APIRouter()


@router.post("")
async def create_work_order(
    wo_in: WorkOrderCreate,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    # 1. Validate Plant
    plant_check = await db.execute(
        select(Plant).where(
            Plant.id == wo_in.plant_id, Plant.company_id == current_company.id
        )
    )
    if not plant_check.scalars().first():
        raise HTTPException(
            status_code=400, detail="Plant not found or does not belong to this company"
        )

    # 2. Validate Product
    product_check = await db.execute(
        select(Product).where(
            Product.id == wo_in.product_id, Product.company_id == current_company.id
        )
    )
    if not product_check.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Product not found or does not belong to this company",
        )

    # 3. Validate Customer (Optional)
    if wo_in.customer_id:
        customer_check = await db.execute(
            select(Customer).where(
                Customer.id == wo_in.customer_id,
                Customer.company_id == current_company.id,
            )
        )
        if not customer_check.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="Customer not found or does not belong to this company",
            )

    # 4. Validate Machine (Optional)
    if wo_in.machine_id:
        machine_check = await db.execute(
            select(Machine).where(
                Machine.id == wo_in.machine_id,
                Machine.company_id == current_company.id,
                Machine.plant_id == wo_in.plant_id,
            )
        )
        if not machine_check.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="Machine not found, belongs to a different company, or is in a different plant",
            )

    # 5. Check uniqueness (company_id, plant_id, order_number)
    existing = await db.execute(
        select(WorkOrder).where(
            WorkOrder.company_id == current_company.id,
            WorkOrder.plant_id == wo_in.plant_id,
            WorkOrder.order_number == wo_in.order_number,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Work Order with this order_number already exists in this plant",
        )

    # 6. Create Work Order
    wo = WorkOrder(
        company_id=current_company.id,
        plant_id=wo_in.plant_id,
        customer_id=wo_in.customer_id,
        product_id=wo_in.product_id,
        machine_id=wo_in.machine_id,
        order_number=wo_in.order_number,
        quantity=wo_in.quantity,
        planned_production_info=wo_in.planned_production_info,
        due_date=wo_in.due_date,
        status=wo_in.status.value,
        production_progress=wo_in.production_progress,
        external_id=wo_in.external_id,
        source_import_job_id=wo_in.source_import_job_id,
    )
    db.add(wo)
    await db.commit()
    await db.refresh(wo)

    return {"data": WorkOrderResponse.model_validate(wo)}


@router.get("")
async def list_work_orders(
    plant_id: str | None = Query(None),
    status: WorkOrderStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(WorkOrder).where(WorkOrder.company_id == current_company.id)

    if plant_id:
        base_query = base_query.where(WorkOrder.plant_id == plant_id)
    if status:
        base_query = base_query.where(WorkOrder.status == status.value)

    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = base_query.order_by(WorkOrder.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    work_orders = result.scalars().all()

    return {
        "data": {
            "items": [WorkOrderResponse.model_validate(wo) for wo in work_orders],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }
