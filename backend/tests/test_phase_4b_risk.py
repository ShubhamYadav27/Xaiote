from datetime import datetime, timedelta, timezone

import pytest

from app.models.impact import ImpactStatus, ProductionOrderImpact
from app.models.risk import RiskState
from app.models.work_order import WorkOrder, WorkOrderStatus
from app.services.risk_evaluator import InsufficientContextException, evaluate


# Test Domain Logic
def test_risk_evaluator_terminal_completed():
    wo = WorkOrder(status=WorkOrderStatus.COMPLETED.value)
    assert evaluate(wo, [], datetime.now(), "UTC") == RiskState.RESOLVED


def test_risk_evaluator_terminal_cancelled():
    wo = WorkOrder(status=WorkOrderStatus.CANCELLED.value)
    assert evaluate(wo, [], datetime.now(), "UTC") == RiskState.NOT_APPLICABLE


def test_risk_evaluator_planned_future():
    wo = WorkOrder(
        status=WorkOrderStatus.PLANNED.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    assert evaluate(wo, [], datetime.now(timezone.utc), "UTC") == RiskState.ON_TRACK


def test_risk_evaluator_in_progress_future():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    assert evaluate(wo, [], datetime.now(timezone.utc), "UTC") == RiskState.ON_TRACK


def test_risk_evaluator_on_hold_future():
    wo = WorkOrder(
        status=WorkOrderStatus.ON_HOLD.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    assert evaluate(wo, [], datetime.now(timezone.utc), "UTC") == RiskState.ON_TRACK


def test_risk_evaluator_on_hold_future_potential():
    wo = WorkOrder(
        status=WorkOrderStatus.ON_HOLD.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    impact = ProductionOrderImpact(status=ImpactStatus.POTENTIAL)
    assert (
        evaluate(wo, [impact], datetime.now(timezone.utc), "UTC")
        == RiskState.PENDING_EVALUATION
    )


def test_risk_evaluator_on_hold_future_confirmed():
    wo = WorkOrder(
        status=WorkOrderStatus.ON_HOLD.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    impact = ProductionOrderImpact(status=ImpactStatus.CONFIRMED)
    assert (
        evaluate(wo, [impact], datetime.now(timezone.utc), "UTC") == RiskState.AT_RISK
    )


def test_risk_evaluator_overdue_no_impacts():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    assert evaluate(wo, [], datetime.now(timezone.utc), "UTC") == RiskState.DELAYED


def test_risk_evaluator_overdue_potential():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    impact = ProductionOrderImpact(status=ImpactStatus.POTENTIAL)
    assert (
        evaluate(wo, [impact], datetime.now(timezone.utc), "UTC") == RiskState.DELAYED
    )


def test_risk_evaluator_overdue_confirmed():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    impact = ProductionOrderImpact(status=ImpactStatus.CONFIRMED)
    assert (
        evaluate(wo, [impact], datetime.now(timezone.utc), "UTC") == RiskState.CRITICAL
    )


def test_risk_evaluator_rejected_overdue():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    impact = ProductionOrderImpact(status=ImpactStatus.REJECTED)
    assert (
        evaluate(wo, [impact], datetime.now(timezone.utc), "UTC") == RiskState.DELAYED
    )


def test_risk_evaluator_rejected_future():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    impact = ProductionOrderImpact(status=ImpactStatus.REJECTED)
    assert (
        evaluate(wo, [impact], datetime.now(timezone.utc), "UTC") == RiskState.ON_TRACK
    )


def test_risk_evaluator_potential_future():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    impact = ProductionOrderImpact(status=ImpactStatus.POTENTIAL)
    assert (
        evaluate(wo, [impact], datetime.now(timezone.utc), "UTC")
        == RiskState.PENDING_EVALUATION
    )


def test_risk_evaluator_confirmed_future():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    impact = ProductionOrderImpact(status=ImpactStatus.CONFIRMED)
    assert (
        evaluate(wo, [impact], datetime.now(timezone.utc), "UTC") == RiskState.AT_RISK
    )


def test_risk_evaluator_multiple_confirmed():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    i1 = ProductionOrderImpact(status=ImpactStatus.CONFIRMED)
    i2 = ProductionOrderImpact(status=ImpactStatus.CONFIRMED)
    assert (
        evaluate(wo, [i1, i2], datetime.now(timezone.utc), "UTC") == RiskState.AT_RISK
    )


def test_risk_evaluator_multiple_potential():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    i1 = ProductionOrderImpact(status=ImpactStatus.POTENTIAL)
    i2 = ProductionOrderImpact(status=ImpactStatus.POTENTIAL)
    assert (
        evaluate(wo, [i1, i2], datetime.now(timezone.utc), "UTC")
        == RiskState.PENDING_EVALUATION
    )


def test_risk_evaluator_null_due_date_no_impact():
    wo = WorkOrder(status=WorkOrderStatus.IN_PROGRESS.value, due_date=None)
    assert evaluate(wo, [], datetime.now(timezone.utc), "UTC") == RiskState.ON_TRACK


def test_risk_evaluator_null_due_date_potential():
    wo = WorkOrder(status=WorkOrderStatus.IN_PROGRESS.value, due_date=None)
    impact = ProductionOrderImpact(status=ImpactStatus.POTENTIAL)
    assert (
        evaluate(wo, [impact], datetime.now(timezone.utc), "UTC")
        == RiskState.PENDING_EVALUATION
    )


def test_risk_evaluator_null_due_date_confirmed():
    wo = WorkOrder(status=WorkOrderStatus.IN_PROGRESS.value, due_date=None)
    impact = ProductionOrderImpact(status=ImpactStatus.CONFIRMED)
    assert (
        evaluate(wo, [impact], datetime.now(timezone.utc), "UTC") == RiskState.AT_RISK
    )


def test_risk_evaluator_exact_time():
    now = datetime.now(timezone.utc)
    wo = WorkOrder(status=WorkOrderStatus.IN_PROGRESS.value, due_date=now)
    assert evaluate(wo, [], now, "UTC") == RiskState.ON_TRACK


def test_risk_evaluator_missing_timezone():
    wo = WorkOrder(
        status=WorkOrderStatus.IN_PROGRESS.value, due_date=datetime.now(timezone.utc)
    )
    with pytest.raises(InsufficientContextException):
        evaluate(wo, [], datetime.now(timezone.utc), None)
