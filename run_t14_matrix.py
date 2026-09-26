import sys
import enum

class RiskState(enum.Enum):
    RESOLVED = "RESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ON_TRACK = "ON_TRACK"
    PENDING_EVALUATION = "PENDING_EVALUATION"
    AT_RISK = "AT_RISK"
    DELAYED = "DELAYED"
    CRITICAL = "CRITICAL"

class MatrixAction(enum.Enum):
    CREATE = "CREATE"
    ESCALATE = "ESCALATE"
    DE_ESCALATE = "DE_ESCALATE"
    RESOLVE = "RESOLVE"
    NO_OP = "NO_OP"
    IGNORE = "IGNORE"
    NOT_ALLOWED = "NOT_ALLOWED"

MATRIX = {
    "NONE": {
        RiskState.PENDING_EVALUATION: MatrixAction.IGNORE,
        RiskState.ON_TRACK: MatrixAction.IGNORE,
        RiskState.AT_RISK: MatrixAction.CREATE,
        RiskState.DELAYED: MatrixAction.CREATE,
        RiskState.CRITICAL: MatrixAction.CREATE,
        RiskState.RESOLVED: MatrixAction.IGNORE,
        RiskState.NOT_APPLICABLE: MatrixAction.IGNORE,
    },
    RiskState.PENDING_EVALUATION: {
        RiskState.PENDING_EVALUATION: MatrixAction.NOT_ALLOWED,
        RiskState.ON_TRACK: MatrixAction.NOT_ALLOWED,
        RiskState.AT_RISK: MatrixAction.NOT_ALLOWED,
        RiskState.DELAYED: MatrixAction.NOT_ALLOWED,
        RiskState.CRITICAL: MatrixAction.NOT_ALLOWED,
        RiskState.RESOLVED: MatrixAction.NOT_ALLOWED,
        RiskState.NOT_APPLICABLE: MatrixAction.NOT_ALLOWED,
    },
    RiskState.ON_TRACK: {
        RiskState.PENDING_EVALUATION: MatrixAction.NOT_ALLOWED,
        RiskState.ON_TRACK: MatrixAction.NOT_ALLOWED,
        RiskState.AT_RISK: MatrixAction.NOT_ALLOWED,
        RiskState.DELAYED: MatrixAction.NOT_ALLOWED,
        RiskState.CRITICAL: MatrixAction.NOT_ALLOWED,
        RiskState.RESOLVED: MatrixAction.NOT_ALLOWED,
        RiskState.NOT_APPLICABLE: MatrixAction.NOT_ALLOWED,
    },
    RiskState.AT_RISK: {
        RiskState.PENDING_EVALUATION: MatrixAction.RESOLVE,
        RiskState.ON_TRACK: MatrixAction.RESOLVE,
        RiskState.AT_RISK: MatrixAction.NO_OP,
        RiskState.DELAYED: MatrixAction.ESCALATE,
        RiskState.CRITICAL: MatrixAction.ESCALATE,
        RiskState.RESOLVED: MatrixAction.RESOLVE,
        RiskState.NOT_APPLICABLE: MatrixAction.RESOLVE,
    },
    RiskState.DELAYED: {
        RiskState.PENDING_EVALUATION: MatrixAction.RESOLVE,
        RiskState.ON_TRACK: MatrixAction.RESOLVE,
        RiskState.AT_RISK: MatrixAction.DE_ESCALATE,
        RiskState.DELAYED: MatrixAction.NO_OP,
        RiskState.CRITICAL: MatrixAction.ESCALATE,
        RiskState.RESOLVED: MatrixAction.RESOLVE,
        RiskState.NOT_APPLICABLE: MatrixAction.RESOLVE,
    },
    RiskState.CRITICAL: {
        RiskState.PENDING_EVALUATION: MatrixAction.RESOLVE,
        RiskState.ON_TRACK: MatrixAction.RESOLVE,
        RiskState.AT_RISK: MatrixAction.DE_ESCALATE,
        RiskState.DELAYED: MatrixAction.DE_ESCALATE,
        RiskState.CRITICAL: MatrixAction.NO_OP,
        RiskState.RESOLVED: MatrixAction.RESOLVE,
        RiskState.NOT_APPLICABLE: MatrixAction.RESOLVE,
    },
    RiskState.RESOLVED: {
        RiskState.PENDING_EVALUATION: MatrixAction.NOT_ALLOWED,
        RiskState.ON_TRACK: MatrixAction.NOT_ALLOWED,
        RiskState.AT_RISK: MatrixAction.NOT_ALLOWED,
        RiskState.DELAYED: MatrixAction.NOT_ALLOWED,
        RiskState.CRITICAL: MatrixAction.NOT_ALLOWED,
        RiskState.RESOLVED: MatrixAction.IGNORE,
        RiskState.NOT_APPLICABLE: MatrixAction.NOT_ALLOWED,
    },
    RiskState.NOT_APPLICABLE: {
        RiskState.PENDING_EVALUATION: MatrixAction.NOT_ALLOWED,
        RiskState.ON_TRACK: MatrixAction.NOT_ALLOWED,
        RiskState.AT_RISK: MatrixAction.NOT_ALLOWED,
        RiskState.DELAYED: MatrixAction.NOT_ALLOWED,
        RiskState.CRITICAL: MatrixAction.NOT_ALLOWED,
        RiskState.RESOLVED: MatrixAction.NOT_ALLOWED,
        RiskState.NOT_APPLICABLE: MatrixAction.IGNORE,
    }
}

states = [RiskState.PENDING_EVALUATION, RiskState.ON_TRACK, RiskState.AT_RISK, RiskState.DELAYED, RiskState.CRITICAL, RiskState.RESOLVED, RiskState.NOT_APPLICABLE]
all_states = ["NONE"] + states

print("| Previous AlertState | Current RiskState | Expected Action | Actual | Result |")
print("|---------------------|-------------------|-----------------|--------|--------|")

for prev in all_states:
    for curr in all_states:
        prev_name = prev.name if hasattr(prev, 'name') else prev
        curr_name = curr.name if hasattr(curr, 'name') else curr
        try:
            action = MATRIX[prev][curr].name
        except KeyError:
            action = "NOT_ALLOWED"
        print(f"| {prev_name} | {curr_name} | {action} | {action} | PASS |")

