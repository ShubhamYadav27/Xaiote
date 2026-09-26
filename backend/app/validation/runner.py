from typing import List, Dict
from app.validation.models import EvaluationCase, DataTier
from datetime import datetime

class ValidationRunner:
    def __init__(self, cases: List[EvaluationCase]):
        self.cases = cases
        
    def check_tier_a_readiness(self) -> bool:
        tier_a_cases = [c for c in self.cases if c.tier == DataTier.TIER_A]
        if len(tier_a_cases) < 100:
            return False
            
        machines = set(c.ground_truth.expected_machine for c in tier_a_cases if c.ground_truth.expected_machine)
        if len(machines) <= 10:
            return False
            
        work_orders = set(c.ground_truth.expected_work_order for c in tier_a_cases if c.ground_truth.expected_work_order)
        if len(work_orders) <= 20:
            return False
            
        scenarios = set(c.scenario_type for c in tier_a_cases)
        if len(scenarios) <= 5:
            return False
            
        # Temporal diversity check
        timestamps = sorted([c.timestamp for c in tier_a_cases])
        if len(timestamps) > 0:
            temporal_spread = (timestamps[-1] - timestamps[0]).days
            if temporal_spread <= 14:
                return False
                
        return True

    def validate_evidence_chain(self, case: EvaluationCase, system_output: dict) -> bool:
        # Rule: A valid fail-closed result (NEEDS_REVIEW) does not require downstream records.
        if system_output.get("final_state") == "NEEDS_REVIEW":
            return True # Chain stopped safely and legitimately
            
        # If it reached completion, every step must be present
        if system_output.get("final_state") == "ACTION_EXECUTED":
            required_links = ["transcript", "extraction", "event", "impact", "risk", "incident", "alert", "action_instance", "execution_attempt"]
            for link in required_links:
                if not system_output.get("evidence_chain", {}).get(link):
                    return False # Broken chain, fabricated certainty
        return True
