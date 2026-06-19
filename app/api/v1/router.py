from fastapi import APIRouter
from app.api.v1.endpoints import contact, health, metrics

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(contact.router, tags=["Contact"])
api_router.include_router(metrics.router, tags=["Metrics"])
