from fastapi import APIRouter,Depends
from src.controllers import review as controller
from src.schemas.entities import ReviewInput,DecisionInput,RevokeInput
from src.services.auth import current,editor,admin
router=APIRouter(prefix="/reviews",tags=["reviews"])
@router.get("")
def list_items(user=Depends(current)): return controller.list_items()
@router.post("",status_code=201)
def create(data:ReviewInput,user=Depends(editor)): return controller.create(data,user)
@router.patch("/{id}")
def decide(id:str,data:DecisionInput,user=Depends(admin)): return controller.decide(id,data,user)
@router.post("/{id}/revoke",status_code=200)
def revoke(id:str,data:RevokeInput,user=Depends(admin)): return controller.revoke(id,data,user)
