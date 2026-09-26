from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.execution import ExecutionAttempt, ExecutionAttemptState
from app.models.actions import ActionInstance
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

class ExecutionMonitoringService:
    @staticmethod
    def generate_execution_health_metrics(db: Session):
        metrics = {
            "CONFIRMATION_TIMEOUT": 0,
            "FAILED": 0,
            "UNKNOWN": 0,
            "ACCEPTED_APPROACHING_TIMEOUT": 0,
            "RECONCILIATION_REQUIRED": 0
        }
        
        stats = db.query(ExecutionAttempt.status, func.count(ExecutionAttempt.id)).filter(
            ExecutionAttempt.status.in_([
                ExecutionAttemptState.CONFIRMATION_TIMEOUT.value,
                ExecutionAttemptState.FAILED.value,
                ExecutionAttemptState.UNKNOWN.value
            ])
        ).group_by(ExecutionAttempt.status).all()
        
        for status, count in stats:
            metrics[status] = count
            
        warning_cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
        approaching_timeout_count = db.query(ExecutionAttempt).filter(
            ExecutionAttempt.status == ExecutionAttemptState.ACCEPTED.value,
            ExecutionAttempt.updated_at < warning_cutoff
        ).count()
        metrics["ACCEPTED_APPROACHING_TIMEOUT"] = approaching_timeout_count

        reconciliation_required_count = db.query(ActionInstance).filter(
            ActionInstance.status == "RECONCILIATION_REQUIRED"
        ).count()
        metrics["RECONCILIATION_REQUIRED"] = reconciliation_required_count

        logger.info(f"Execution Health Metrics: {metrics}")
        return metrics
