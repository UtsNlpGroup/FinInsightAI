"""
Aggregates all v1 endpoint routers.

Adding a new resource is as simple as importing its router here and calling
`v1_router.include_router(...)`.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.agent    import router as agent_router
from app.api.v1.endpoints.analysis import router as analysis_router
from app.api.v1.endpoints.chat     import router as chat_router
from app.api.v1.endpoints.market   import router as market_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(agent_router)
v1_router.include_router(analysis_router)
v1_router.include_router(chat_router)
v1_router.include_router(market_router)
