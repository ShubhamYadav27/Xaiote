from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_company
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.masters import Product
from app.schemas.masters import ProductCreate, ProductResponse

router = APIRouter()


@router.post("")
async def create_product(
    product_in: ProductCreate,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    if product_in.external_id:
        existing = await db.execute(
            select(Product).where(
                Product.company_id == current_company.id,
                Product.external_id == product_in.external_id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=400, detail="Product with this external_id already exists"
            )

    product = Product(
        company_id=current_company.id,
        name=product_in.name,
        sku=product_in.sku,
        external_id=product_in.external_id,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return {"data": ProductResponse.model_validate(product)}


@router.get("")
async def list_products(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(Product).where(Product.company_id == current_company.id)
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = base_query.order_by(Product.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()

    return {
        "data": {
            "items": [ProductResponse.model_validate(p) for p in products],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }
