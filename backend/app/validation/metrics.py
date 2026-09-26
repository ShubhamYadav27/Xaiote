from typing import List
from app.validation.models import EvaluationCase, MetricResult, DataTier

class ValidationMetricsEngine:
    MIN_SAMPLE_SIZE = 50

    @classmethod
    def calculate_metric(
        cls, 
        metric_name: str, 
        tier: DataTier, 
        evaluations: List[dict]
    ) -> MetricResult:
        
        valid_evals = [e for e in evaluations if e['is_applicable']]
        denominator = len(valid_evals)
        
        if denominator < cls.MIN_SAMPLE_SIZE:
            return MetricResult(
                metric_name=metric_name,
                numerator=sum(e['is_successful'] for e in valid_evals),
                denominator=denominator,
                percentage=None,
                sample_size=denominator,
                tier=tier,
                status="INSUFFICIENT_EVIDENCE"
            )
            
        numerator = sum(e['is_successful'] for e in valid_evals)
        percentage = (numerator / denominator) * 100.0
        
        # Simplified hard-gate mock (in real system, thresholds vary by metric)
        status = "PASSED" if percentage >= 90.0 else "FAILED"
        
        return MetricResult(
            metric_name=metric_name,
            numerator=numerator,
            denominator=denominator,
            percentage=percentage,
            sample_size=denominator,
            tier=tier,
            status=status,
            confidence_interval=f"+/- 3.0%" # placeholder for standard error math
        )
