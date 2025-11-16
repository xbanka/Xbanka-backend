from fastapi import APIRouter, Depends
from app.utils.auth import require_role

erp = APIRouter(prefix="/erp", tags=["ERP"])

@erp.get("/")
def get_index(user = Depends(require_role("erp"))):
    return {
        "message": "hey"
    }