"""
Health Check Endpoint
"""
from fastapi import APIRouter, HTTPException
from app.models.response import HealthResponse
from app.utils.agent_wrapper import AgentManager
from app.config import settings
import sys
from pathlib import Path

# Add project root to path for cache manager
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from snowflake.agents.cache_manager import get_cache

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns:
        - API status
        - Version
        - Agent connectivity status
        - Snowflake connectivity
        - Cache health (Redis + in-memory)
    """
    try:
        # Test agent connections
        agent_status = AgentManager.test_connections()

        # Check cache health
        cache = get_cache()
        cache_health = cache.health_check()

        # Determine Snowflake status
        snowflake_healthy = all(
            "healthy" in status
            for status in agent_status.values()
        )

        # Overall status
        overall_status = "healthy"
        if not snowflake_healthy:
            overall_status = "degraded"
        if cache_health["status"] == "degraded":
            overall_status = "degraded"

        response_data = {
            "status": overall_status,
            "version": settings.VERSION,
            "agents": agent_status,
            "snowflake": "connected" if snowflake_healthy else "connection issues",
            "cache": cache_health
        }

        return HealthResponse(**response_data)

    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            version=settings.VERSION,
            agents={
                "agent1": "unknown",
                "agent3": "unknown",
                "agent4": "unknown"
            },
            snowflake=f"error: {str(e)}",
            cache={"status": "unknown", "error": str(e)}
        )