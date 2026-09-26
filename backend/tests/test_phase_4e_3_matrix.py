from app.models.risk import RiskState
from app.services.alert_evaluator import MatrixAction, get_matrix_action


def test_t14_64_cell_matrix():
    # 7 risk states + 1 synthetic NONE state
    states = [RiskState.PENDING_EVALUATION, RiskState.ON_TRACK, RiskState.AT_RISK, RiskState.DELAYED, RiskState.CRITICAL, RiskState.RESOLVED, RiskState.NOT_APPLICABLE]
    all_states = ["NONE"] + states
    
    count = 0
    for prev in all_states:
        for curr in all_states:
            if curr == "NONE":
                # Current risk state can never be NONE in a valid db state.
                # get_matrix_action will raise KeyError, which means NOT_ALLOWED.
                try:
                    action = get_matrix_action(prev, curr)
                    assert False, "Should raise KeyError for NONE current state"
                except KeyError:
                    pass
            else:
                action = get_matrix_action(prev, curr)
                assert isinstance(action, MatrixAction)
            count += 1
            
    assert count == 64
