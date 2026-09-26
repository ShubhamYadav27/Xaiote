from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.approval_service import ApprovalDomainService

def get_db(): yield None
def get_current_user(): return type('User', (), {'id': 'u1', 'company_id': 'c1', 'role': 'PLANT_HEAD'})()

router = APIRouter(prefix="/api/v1/actions/instances", tags=["Human Approvals"])

class ApprovalRequest(BaseModel):
    expected_version: int
    reason: str = None

class RejectionRequest(BaseModel):
    expected_version: int
    reason: str

class ApprovalResponse(BaseModel):
    id: str
    status: str

@router.post("/{id}/approve", response_model=ApprovalResponse)
def approve_action_endpoint(id: str, req: ApprovalRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        action = ApprovalDomainService.approve_action(
            db=db,
            action_id=id,
            expected_version=req.expected_version,
            user_id=current_user.id,
            user_role=current_user.role,
            user_company_id=current_user.company_id,
            reason=req.reason
        )
        return ApprovalResponse(id=action.id, status=action.status)
    except ValueError as e:
        msg = str(e)
        if "OCC mismatch" in msg or "Terminal or invalid state" in msg or "Serialization conflict" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "Unauthorized" in msg or "Cross-tenant" in msg:
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

@router.post("/{id}/reject", response_model=ApprovalResponse)
def reject_action_endpoint(id: str, req: RejectionRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        action = ApprovalDomainService.reject_action(
            db=db,
            action_id=id,
            expected_version=req.expected_version,
            user_id=current_user.id,
            user_role=current_user.role,
            user_company_id=current_user.company_id,
            reason=req.reason
        )
        return ApprovalResponse(id=action.id, status=action.status)
    except ValueError as e:
        msg = str(e)
        if "OCC mismatch" in msg or "Terminal or invalid state" in msg or "Serialization conflict" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "Unauthorized" in msg or "Cross-tenant" in msg:
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
