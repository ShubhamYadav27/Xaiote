from datetime import datetime

from app.models.impact import ImpactStatus, ProductionOrderImpact
from app.models.risk import RiskState
from app.models.work_order import WorkOrder, WorkOrderStatus


class InsufficientContextException(Exception):
    def __init__(self, message: str = "Missing required context for risk evaluation"):
        self.message = message
        super().__init__(self.message)


def evaluate(
    work_order: WorkOrder,
    impacts: list[ProductionOrderImpact],
    evaluation_time: datetime,
    plant_timezone: str | None = None,
) -> RiskState:
    # 1. Terminal Check
    if work_order.status == WorkOrderStatus.COMPLETED.value:
        return RiskState.RESOLVED
    if work_order.status == WorkOrderStatus.CANCELLED.value:
        return RiskState.NOT_APPLICABLE

    # 2. Timezone Context
    # Based on the prompt: If plant timezone is required by the WorkOrder due-date semantic contract
    # and timezone context is missing: raise InsufficientContextException
    # Since we treat due_date as an exact timestamp (DateTime timezone=True), the comparison
    # evaluation_time > due_date is native to Python if both are tz-aware.
    # However, the requirement says "If the contract defines due_date as a business date:
    # interpret that date as plant-local end-of-day."
    # For now, let's assume the contract ALWAYS requires timezone context to safely normalize
    # or compare due dates reliably in Xaiote, as requested:
    if work_order.due_date is not None and plant_timezone is None:
        raise InsufficientContextException("Missing required plant timezone context.")

    # 3. Impact Aggregation
    # Phase 4C: Incorporate Incident.status. Legacy incident_id=NULL impacts preserve existing behavior.
    active_impacts = []
    for i in impacts:
        if getattr(i, "incident_id", None) and getattr(i, "incident", None):
            # Only count if the incident is ACTIVE
            if getattr(i.incident.status, "value", i.incident.status) != "ACTIVE":
                continue
        active_impacts.append(i)

    has_confirmed = any(i.status == ImpactStatus.CONFIRMED for i in active_impacts)
    has_potential = any(i.status == ImpactStatus.POTENTIAL for i in active_impacts)

    # 4. Due Date
    is_overdue = False
    if work_order.due_date is not None:
        # Strict exact timestamp comparison as mandated for Phase 4B
        is_overdue = evaluation_time > work_order.due_date

    # 5. State Resolution
    if is_overdue and has_confirmed:
        return RiskState.CRITICAL
    elif is_overdue and not has_confirmed:
        return RiskState.DELAYED
    elif not is_overdue and has_confirmed:
        return RiskState.AT_RISK
    elif not is_overdue and has_potential:
        return RiskState.PENDING_EVALUATION
    else:
        return RiskState.ON_TRACK
