from fastapi import APIRouter
from .auth import auth as auth_router
from .dashboard import dashboard as dashboard_router

api_version_one = APIRouter(prefix='/api')

api_version_one.include_router(auth_router)
api_version_one.include_router(dashboard_router)