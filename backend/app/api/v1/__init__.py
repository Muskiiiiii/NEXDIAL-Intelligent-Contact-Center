from fastapi import APIRouter
from app.api.v1.agents import router as agents_router
from app.api.v1.borrowers import router as borrowers_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.calls import router as calls_router
from app.api.v1.safety import router as safety_router
from app.api.v1.pacing import router as pacing_router
from app.api.v1.providers import router as providers_router
from app.api.v1.workers import router as workers_router
from app.api.v1.simulation import router as simulation_router
from app.api.v1.failures import router as failures_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.architecture import router as architecture_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(agents_router)
api_v1_router.include_router(borrowers_router)
api_v1_router.include_router(campaigns_router)
api_v1_router.include_router(calls_router)
api_v1_router.include_router(safety_router)
api_v1_router.include_router(pacing_router)
api_v1_router.include_router(providers_router)
api_v1_router.include_router(workers_router)
api_v1_router.include_router(simulation_router)
api_v1_router.include_router(failures_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(architecture_router)
