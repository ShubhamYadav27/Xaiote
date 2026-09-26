from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.execution_gateway import ExecutionGatewayService

def get_db(): yield None
def get_current_user(): return type('User', (), {'id': 'u1', 'company_id': 'c1', 'role': 'PLANT_HEAD'})()

router = APIRouter(prefix="/api/v1/actions/instances", tags=["Execution Gateway"])

class ExecutionRequest(BaseModel):
    expected_version: int

class ExecutionResponse(BaseModel):
    action_instance_id: str
    execution_attempt_id: str
    status: str
    correlation_id: str = None

@router.post("/{id}/execute", response_model=ExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
def request_execution_endpoint(id: str, req: ExecutionRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        attempt = ExecutionGatewayService.request_execution(
            db=db,
            action_id=id,
            expected_version=req.expected_version,
            user_id=current_user.id,
            user_role=current_user.role,
            user_company_id=current_user.company_id
        )
        return ExecutionResponse(
            action_instance_id=attempt.action_instance_id,
            execution_attempt_id=attempt.id,
            status=attempt.status,
            correlation_id=attempt.external_correlation_id
        )
    except ValueError as e:
        msg = str(e)
        if "OCC mismatch" in msg or "Terminal or invalid state" in msg or "Serialization conflict" in msg or "already been successfully executed" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "Unauthorized" in msg or "Cross-tenant" in msg:
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
