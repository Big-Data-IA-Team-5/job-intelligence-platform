"""
Health Check Endpoint
"""
from fastapi import APIRouter, HTTPException
from app.models.response import HealthResponse
from app.utils.agent_wrapper import AgentManager
from app.config import settings

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
    """
    try:
        # Test agent connections
        agent_status = AgentManager.test_connections()
        
        # Determine Snowflake status
        snowflake_healthy = all(
            "healthy" in status 
            for status in agent_status.values()
        )
        
        return HealthResponse(
            status="healthy" if snowflake_healthy else "degraded",
            version=settings.VERSION,
            agents=agent_status,
            snowflake="connected" if snowflake_healthy else "connection issues"
        )
    
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            version=settings.VERSION,
            agents={
                "agent1": "unknown",
                "agent3": "unknown",
                "agent4": "unknown"
            },
            snowflake=f"error: {str(e)}"
        )