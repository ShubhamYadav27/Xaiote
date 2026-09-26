import re

with open(r'C:\Xaiote\backend\app\models\alerts.py', 'r', encoding='utf-8') as f:
    t = f.read()

new_enums = '''
class AlertEvaluationJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
'''

t = t.replace('class AlertSeverity(str, enum.Enum):', new_enums + '\nclass AlertSeverity(str, enum.Enum):')

job_model = '''
class AlertEvaluationJob(Base):
    __tablename__ = "alert_evaluation_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=False)

    target_work_order_id = Column(String, ForeignKey("work_orders.id"), nullable=True)
    target_incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)

    status = Column(String, default=AlertEvaluationJobStatus.PENDING.value, nullable=False)
    worker_id = Column(String, nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    error_detail = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN target_work_order_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN target_incident_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_alert_eval_job_target_xor"
        ),
    )
'''

t = t + '\n' + job_model

with open(r'C:\Xaiote\backend\app\models\alerts.py', 'w', encoding='utf-8') as f:
    f.write(t)
