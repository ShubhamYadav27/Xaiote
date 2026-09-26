from sqlalchemy.orm import Session
from app.models.user_plants import UserPlant

class PlantAuthorizationService:
    
    @staticmethod
    def is_plant_authorized(db: Session, user_id: str, company_id: str, role: str, target_plant_id: str) -> bool:
        """
        Evaluates whether a user is authorized for a specific plant.
        """
        if role in ["ADMIN", "OWNER"]:
            return True
            
        auth_record = db.query(UserPlant).filter_by(
            company_id=company_id,
            user_id=user_id,
            plant_id=target_plant_id
        ).first()
        
        return auth_record is not None
