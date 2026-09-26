import pytest
from datetime import datetime, timedelta
from app.validation.models import EvaluationCase, GroundTruth, DataTier
from app.validation.runner import ValidationRunner
from app.validation.metrics import ValidationMetricsEngine

def test_tier_a_gating():
    # Provide insufficient data
    cases = [
        EvaluationCase(
            case_id=f"c_{i}",
            tier=DataTier.TIER_A,
            source_type="audio",
            scenario_type="machine_failure",
            raw_evidence="test",
            ground_truth=GroundTruth(expected_machine="M1", expected_work_order="WO1"),
            timestamp=datetime.utcnow()
        ) for i in range(10)
    ]
    runner = ValidationRunner(cases)
    assert runner.check_tier_a_readiness() is False

def test_metric_insufficient_evidence():
    evals = [{"is_applicable": True, "is_successful": True} for _ in range(49)]
    result = ValidationMetricsEngine.calculate_metric("A_EVIDENCE_EXTRACTION", DataTier.TIER_A, evals)
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.percentage is None

def test_evidence_chain_fail_closed_is_safe():
    runner = ValidationRunner([])
    # System outputs NEEDS_REVIEW. It shouldn't be penalized for lacking downstream records.
    sys_out = {"final_state": "NEEDS_REVIEW", "evidence_chain": {"transcript": "x"}}
    assert runner.validate_evidence_chain(EvaluationCase(
        case_id="1", tier=DataTier.TIER_B, source_type="audio", scenario_type="x", raw_evidence="x", ground_truth=GroundTruth()
    ), sys_out) is True

def test_evidence_chain_fabricated_certainty_fails():
    runner = ValidationRunner([])
    # System claims ACTION_EXECUTED but lacks 'impact' or 'risk' evidence
    sys_out = {"final_state": "ACTION_EXECUTED", "evidence_chain": {"transcript": "x", "action_instance": "y"}}
    assert runner.validate_evidence_chain(EvaluationCase(
        case_id="1", tier=DataTier.TIER_B, source_type="audio", scenario_type="x", raw_evidence="x", ground_truth=GroundTruth()
    ), sys_out) is False
