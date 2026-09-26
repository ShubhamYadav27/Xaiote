from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class DataTier(str, Enum):
    TIER_A = "TIER_A"
    TIER_B = "TIER_B"
    TIER_C = "TIER_C"

class GroundTruthState(str, Enum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    AMBIGUOUS = "AMBIGUOUS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class GroundTruth(BaseModel):
    expected_event_type: Optional[str] = None
    expected_machine: Optional[str] = None
    expected_work_order: Optional[str] = None
    expected_customer: Optional[str] = None
    expected_product: Optional[str] = None
    expected_vendor: Optional[str] = None
    expected_downtime: Optional[int] = None
    expected_severity: Optional[str] = None
    expected_temporal_interpretation: Optional[str] = None
    expected_impact: Optional[str] = None
    expected_risk: Optional[str] = None
    expected_incident_relationship: Optional[str] = None
    expected_root_cause: Optional[str] = None
    expected_alert_behavior: Optional[str] = None
    expected_recommendation: Optional[str] = None
    expected_action_outcome: Optional[str] = None
    acceptable_uncertainty: bool = False

class EvaluationCase(BaseModel):
    case_id: str
    tier: DataTier
    source_type: str
    scenario_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_evidence: str
    ground_truth: GroundTruth

class MetricResult(BaseModel):
    metric_name: str
    numerator: int
    denominator: int
    percentage: Optional[float] = None
    sample_size: int
    tier: DataTier
    status: str # e.g. "PASSED", "FAILED", "INSUFFICIENT_EVIDENCE"
    confidence_interval: Optional[str] = None

class HumanEvaluation(BaseModel):
    evaluator_id: str
    evaluator_role: str
    case_id: str
    factual_correctness: int
    evidence_quality: int
    trust: int
    actionability: int
    usefulness: int
    correction_effort: int

class BusinessValueMeasurement(BaseModel):
    investigation_time_saved_minutes: Optional[int] = None
    coordination_effort_reduction: Optional[str] = None
    time_to_identify_orders_minutes: Optional[int] = None
    escalation_time_minutes: Optional[int] = None
    missed_operational_risks_prevented: Optional[int] = None
