"""
Agent Wrapper - Connects FastAPI to Snowflake Agents
"""
import sys
from pathlib import Path

# Add snowflake/agents to path
agents_path = Path(__file__).parents[3] / 'snowflake' / 'agents'
sys.path.insert(0, str(agents_path))

from agent1_search import JobSearchAgent
from agent3_classifier import VisaClassifier
from agent4_matcher import ResumeMatcherAgent

class AgentManager:
    """Manages connections to all 3 agents"""
    
    @staticmethod
    def get_search_agent():
        """Get Job Search Agent (Agent 1)"""
        return JobSearchAgent()
    
    @staticmethod
    def get_classifier():
        """Get Visa Classifier (Agent 3)"""
        return VisaClassifier()
    
    @staticmethod
    def get_matcher():
        """Get Resume Matcher (Agent 4)"""
        return ResumeMatcherAgent()
    
    @staticmethod
    def test_connections():
        """Test all agent connections"""
        results = {
            "agent1": "unknown",
            "agent3": "unknown",
            "agent4": "unknown"
        }
        
        # Test Agent 1
        try:
            agent = JobSearchAgent()
            agent.close()
            results["agent1"] = "healthy"
        except Exception as e:
            results["agent1"] = f"error: {str(e)}"
        
        # Test Agent 3
        try:
            agent = VisaClassifier()
            agent.close()
            results["agent3"] = "healthy"
        except Exception as e:
            results["agent3"] = f"error: {str(e)}"
        
        # Test Agent 4
        try:
            agent = ResumeMatcherAgent()
            agent.close()
            results["agent4"] = "healthy"
        except Exception as e:
            results["agent4"] = f"error: {str(e)}"
        
        return results