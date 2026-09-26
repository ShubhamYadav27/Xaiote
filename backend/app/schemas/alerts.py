from datetime import datetime

from pydantic import BaseModel

from app.models.alerts import AlertSeverity, AlertStatus


class AlertPolicyBase(BaseModel):
    name: str
    is_active: bool = True


class AlertPolicyCreate(AlertPolicyBase):
    pass


class AlertPolicyResponse(AlertPolicyBase):
    id: str
    company_id: str
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertRuleBase(BaseModel):
    alert_family: str
    severity: AlertSeverity
    trigger_condition: dict
    clear_condition: dict


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleResponse(AlertRuleBase):
    id: str
    company_id: str
    version: int
    policy_id: str
    policy_version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertInstanceResponse(BaseModel):
    id: str
    company_id: str
    plant_id: str
    alert_family: str
    target_work_order_id: str | None = None
    target_incident_id: str | None = None
    originating_policy_id: str
    originating_policy_version: int
    originating_rule_id: str
    originating_rule_version: int
    current_policy_id: str
    current_policy_version: int
    current_rule_id: str
    current_rule_version: int
    status: AlertStatus
    severity: AlertSeverity
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):
    id: str
    alert_instance_id: str
    company_id: str
    action: str
    previous_severity: AlertSeverity | None = None
    new_severity: AlertSeverity | None = None
    previous_policy_id: str | None = None
    previous_policy_version: int | None = None
    previous_rule_id: str | None = None
    previous_rule_version: int | None = None
    new_policy_id: str | None = None
    new_policy_version: int | None = None
    new_rule_id: str | None = None
    new_rule_version: int | None = None
    actor_id: str | None = None
    timestamp: datetime

    class Config:
        from_attributes = True


class AlertEvidenceLinkResponse(BaseModel):
    id: str
    alert_instance_id: str
    company_id: str
    evidence_manufacturing_event_id: str | None = None
    evidence_production_order_impact_id: str | None = None
    evidence_risk_history_id: str | None = None
    evidence_root_cause_assessment_id: str | None = None

    class Config:
        from_attributes = True
