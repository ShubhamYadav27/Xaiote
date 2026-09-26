import hashlib

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_company, get_current_user
from app.infrastructure.database.session import get_db
from app.infrastructure.storage.s3_storage import get_storage
from app.models.company import Company
from app.models.imports import ImportAudit, ImportEntityType, ImportJob
from app.models.user import User
from app.schemas.imports import ImportAuditResponse, ImportJobResponse
from app.services.import_processor import process_import_job

router = APIRouter()


@router.post("/upload")
async def upload_import(
    file: UploadFile = File(...),
    import_type: ImportEntityType = Form(...),
    current_company: Company = Depends(get_current_company),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    contents = await file.read()
    file_size = len(contents)

    if file_size > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 25 MB limit")

    file_hash = hashlib.sha256(contents).hexdigest()
    object_name = f"{current_company.id}/{file_hash}"

    # Check duplicate file
    existing = await db.execute(
        select(ImportJob).where(
            ImportJob.company_id == current_company.id,
            ImportJob.source_file_hash == object_name,
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="File has already been uploaded")

    storage = get_storage()
    await storage.upload("imports", object_name, contents)

    job = ImportJob(
        company_id=current_company.id,
        created_by=current_user.id,
        import_type=import_type.value,
        source_filename=file.filename,
        source_file_hash=object_name,
        file_size=file_size,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Synchronously process the job for MVP
    await process_import_job(job.id, db)
    await db.refresh(job)

    return {"data": ImportJobResponse.model_validate(job)}


@router.get("/{job_id}")
async def get_import_job(
    job_id: str,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ImportJob).where(
            ImportJob.id == job_id, ImportJob.company_id == current_company.id
        )
    )
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Import Job not found")

    return {"data": ImportJobResponse.model_validate(job)}


@router.get("/{job_id}/audits")
async def get_import_audits(
    job_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    result = await db.execute(
        select(ImportJob).where(
            ImportJob.id == job_id, ImportJob.company_id == current_company.id
        )
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Import Job not found")

    base_query = select(ImportAudit).where(ImportAudit.import_job_id == job_id)

    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        base_query.order_by(ImportAudit.source_row_number.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    audits = result.scalars().all()

    return {
        "data": {
            "items": [ImportAuditResponse.model_validate(a) for a in audits],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }
