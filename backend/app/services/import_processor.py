import csv
import io

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.infrastructure.storage.s3_storage import get_storage
from app.models.imports import (
    ImportAudit,
    ImportAuditAction,
    ImportEntityType,
    ImportJob,
    ImportJobStatus,
    ValidationStatus,
)
from app.models.masters import Customer, Machine, Product, Vendor
from app.models.work_order import WorkOrder


async def process_import_job(job_id: str, db: AsyncSession):
    # 1. Fetch Job
    result = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
    job = result.scalars().first()
    if not job or job.status != ImportJobStatus.RECEIVED.value:
        return

    # Transition to VALIDATING
    job.status = ImportJobStatus.VALIDATING.value
    db.add(job)
    await db.commit()

    storage = get_storage()
    try:
        file_bytes = await storage.download("imports", job.source_file_hash)
        content = file_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))

        # Count rows (could be done via stream to avoid memory, but max is 50k)
        rows = list(reader)
        job.total_rows = len(rows)

        if job.total_rows > 50000:
            job.status = ImportJobStatus.FAILED.value
            job.error_message = "Exceeded 50,000 rows limit"
            db.add(job)
            await db.commit()
            return

        # Transition to PROCESSING
        job.status = ImportJobStatus.PROCESSING.value
        db.add(job)
        await db.commit()

        valid_count = 0
        invalid_count = 0
        needs_review_count = 0
        created_count = 0
        updated_count = 0
        unchanged_count = 0

        for idx, row in enumerate(rows):
            source_row_number = idx + 2  # Header is 1

            # Dispatch based on entity type
            # Return tuple: (success, reason, target_record_id, action, previous_source_import_job_id, needs_review)
            if job.import_type == ImportEntityType.CUSTOMERS.value:
                res = await process_customer_row(job.company_id, row, job.id, db)
            elif job.import_type == ImportEntityType.VENDORS.value:
                res = await process_vendor_row(job.company_id, row, job.id, db)
            elif job.import_type == ImportEntityType.PRODUCTS.value:
                res = await process_product_row(job.company_id, row, job.id, db)
            elif job.import_type == ImportEntityType.MACHINES.value:
                res = await process_machine_row(job.company_id, row, job.id, db)
            elif job.import_type == ImportEntityType.WORK_ORDERS.value:
                res = await process_work_order_row(job.company_id, row, job.id, db)
            else:
                res = (False, "Unknown import type", None, None, None, False)

            success, reason, target_record_id, action, previous_job_id, needs_review = (
                res
            )

            validation_status = ValidationStatus.VALID.value
            if not success:
                validation_status = ValidationStatus.INVALID.value
            elif needs_review:
                validation_status = ValidationStatus.NEEDS_REVIEW.value

            audit = ImportAudit(
                import_job_id=job.id,
                source_row_number=source_row_number,
                target_entity_type=job.import_type,
                target_record_id=target_record_id,
                validation_status=validation_status,
                validation_reason=reason if (not success or needs_review) else None,
                action=action,
                previous_source_import_job_id=previous_job_id,
            )
            db.add(audit)

            if not success:
                invalid_count += 1
            else:
                valid_count += 1
                if needs_review:
                    needs_review_count += 1

                if action == ImportAuditAction.CREATED.value:
                    created_count += 1
                elif action == ImportAuditAction.UPDATED.value:
                    updated_count += 1
                elif action == ImportAuditAction.UNCHANGED.value:
                    unchanged_count += 1

            if idx % 100 == 0:
                await db.commit()

        job.valid_rows = valid_count
        job.invalid_rows = invalid_count
        job.needs_review_rows = needs_review_count
        job.created_rows = created_count
        job.updated_rows = updated_count
        job.unchanged_rows = unchanged_count

        job.status = (
            ImportJobStatus.COMPLETED.value
            if invalid_count == 0
            else ImportJobStatus.COMPLETED_WITH_ERRORS.value
        )
        db.add(job)
        await db.commit()

    except Exception as e:  # noqa: BLE001
        job.status = ImportJobStatus.FAILED.value
        job.error_message = str(e)
        db.add(job)
        await db.commit()


async def process_customer_row(
    company_id: str, row: dict[str, str], job_id: str, db: AsyncSession
):
    name = row.get("name", "").strip()
    external_id = row.get("external_id", "").strip()
    if not name:
        return False, "Name is required", None, None, None, False

    result = await db.execute(
        select(Customer).where(
            Customer.company_id == company_id, Customer.external_id == external_id
        )
    )
    existing = result.scalars().first()

    if existing:
        prev_job_id = existing.source_import_job_id
        if existing.name != name:
            existing.name = name
            existing.source_import_job_id = job_id
            db.add(existing)
            await db.flush()
            return (
                True,
                None,
                existing.id,
                ImportAuditAction.UPDATED.value,
                prev_job_id,
                False,
            )
        else:
            return (
                True,
                None,
                existing.id,
                ImportAuditAction.UNCHANGED.value,
                prev_job_id,
                False,
            )

    customer = Customer(
        company_id=company_id,
        name=name,
        external_id=external_id,
        source_import_job_id=job_id,
    )
    db.add(customer)
    await db.flush()
    return True, None, customer.id, ImportAuditAction.CREATED.value, None, False


async def process_vendor_row(
    company_id: str, row: dict[str, str], job_id: str, db: AsyncSession
):
    name = row.get("name", "").strip()
    external_id = row.get("external_id", "").strip()
    if not name:
        return False, "Name is required", None, None, None, False

    result = await db.execute(
        select(Vendor).where(
            Vendor.company_id == company_id, Vendor.external_id == external_id
        )
    )
    existing = result.scalars().first()

    if existing:
        prev_job_id = existing.source_import_job_id
        if existing.name != name:
            existing.name = name
            existing.source_import_job_id = job_id
            db.add(existing)
            await db.flush()
            return (
                True,
                None,
                existing.id,
                ImportAuditAction.UPDATED.value,
                prev_job_id,
                False,
            )
        else:
            return (
                True,
                None,
                existing.id,
                ImportAuditAction.UNCHANGED.value,
                prev_job_id,
                False,
            )

    vendor = Vendor(
        company_id=company_id,
        name=name,
        external_id=external_id,
        source_import_job_id=job_id,
    )
    db.add(vendor)
    await db.flush()
    return True, None, vendor.id, ImportAuditAction.CREATED.value, None, False


async def process_product_row(
    company_id: str, row: dict[str, str], job_id: str, db: AsyncSession
):
    name = row.get("name", "").strip()
    external_id = row.get("external_id", "").strip()
    if not name:
        return False, "Name is required", None, None, None, False

    result = await db.execute(
        select(Product).where(
            Product.company_id == company_id, Product.external_id == external_id
        )
    )
    existing = result.scalars().first()

    if existing:
        prev_job_id = existing.source_import_job_id
        if existing.name != name:
            existing.name = name
            existing.source_import_job_id = job_id
            db.add(existing)
            await db.flush()
            return (
                True,
                None,
                existing.id,
                ImportAuditAction.UPDATED.value,
                prev_job_id,
                False,
            )
        else:
            return (
                True,
                None,
                existing.id,
                ImportAuditAction.UNCHANGED.value,
                prev_job_id,
                False,
            )

    product = Product(
        company_id=company_id,
        name=name,
        external_id=external_id,
        source_import_job_id=job_id,
    )
    db.add(product)
    await db.flush()
    return True, None, product.id, ImportAuditAction.CREATED.value, None, False


async def process_machine_row(
    company_id: str, row: dict[str, str], job_id: str, db: AsyncSession
):
    name = row.get("name", "").strip()
    plant_id = row.get("plant_id", "").strip()
    external_id = row.get("external_id", "").strip()
    if not name or not plant_id:
        return False, "Name and plant_id are required", None, None, None, False

    result = await db.execute(
        select(Machine).where(
            Machine.company_id == company_id,
            Machine.plant_id == plant_id,
            Machine.external_id == external_id,
        )
    )
    existing = result.scalars().first()

    if existing:
        prev_job_id = existing.source_import_job_id
        if existing.name != name:
            existing.name = name
            existing.source_import_job_id = job_id
            db.add(existing)
            await db.flush()
            return (
                True,
                None,
                existing.id,
                ImportAuditAction.UPDATED.value,
                prev_job_id,
                False,
            )
        else:
            return (
                True,
                None,
                existing.id,
                ImportAuditAction.UNCHANGED.value,
                prev_job_id,
                False,
            )

    machine = Machine(
        company_id=company_id,
        plant_id=plant_id,
        name=name,
        external_id=external_id,
        source_import_job_id=job_id,
    )
    db.add(machine)
    await db.flush()
    return True, None, machine.id, ImportAuditAction.CREATED.value, None, False


async def process_work_order_row(
    company_id: str, row: dict[str, str], job_id: str, db: AsyncSession
):
    order_number = row.get("order_number", "").strip()
    plant_id = row.get("plant_id", "").strip()
    product_id = row.get("product_id", "").strip()
    quantity = row.get("quantity", "0").strip()

    if not order_number or not plant_id or not product_id:
        return (
            False,
            "order_number, plant_id, and product_id are required",
            None,
            None,
            None,
            False,
        )

    try:
        qty = float(quantity)
        if qty < 0:
            return False, "Quantity cannot be negative", None, None, None, False
    except ValueError:
        return False, "Quantity must be numeric", None, None, None, False

    # Validate FKs
    from app.models.plant import Plant

    plant = (
        (
            await db.execute(
                select(Plant).where(
                    Plant.id == plant_id, Plant.company_id == company_id
                )
            )
        )
        .scalars()
        .first()
    )
    if not plant:
        return (
            False,
            "Plant reference is unknown or belongs to another company",
            None,
            None,
            None,
            False,
        )

    product = (
        (
            await db.execute(
                select(Product).where(
                    Product.id == product_id, Product.company_id == company_id
                )
            )
        )
        .scalars()
        .first()
    )
    if not product:
        return (
            False,
            "Product reference is unknown or belongs to another company",
            None,
            None,
            None,
            False,
        )

    result = await db.execute(
        select(WorkOrder).where(
            WorkOrder.company_id == company_id,
            WorkOrder.plant_id == plant_id,
            WorkOrder.order_number == order_number,
        )
    )
    existing = result.scalars().first()

    needs_review = qty == 0
    reason = "Quantity is zero" if needs_review else None

    if existing:
        prev_job_id = existing.source_import_job_id
        if existing.quantity != qty:
            existing.quantity = qty
            existing.source_import_job_id = job_id
            db.add(existing)
            await db.flush()
            return (
                True,
                reason,
                existing.id,
                ImportAuditAction.UPDATED.value,
                prev_job_id,
                needs_review,
            )
        else:
            return (
                True,
                reason,
                existing.id,
                ImportAuditAction.UNCHANGED.value,
                prev_job_id,
                needs_review,
            )

    wo = WorkOrder(
        company_id=company_id,
        plant_id=plant_id,
        product_id=product_id,
        order_number=order_number,
        quantity=qty,
        source_import_job_id=job_id,
    )
    db.add(wo)
    await db.flush()
    return True, reason, wo.id, ImportAuditAction.CREATED.value, None, needs_review
