"""
Frontend Component Tests
Tests Streamlit UI components and interactions
"""
import pytest
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "frontend"))


@pytest.mark.unit
class TestFrontendUtils:
    """Test frontend utility modules."""
    
    def test_context_manager_import(self):
        """Test that context manager can be imported."""
        try:
            from utils.context_manager import ConversationContext
            assert ConversationContext is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ConversationContext: {e}")
    
    def test_api_client_import(self):
        """Test that API client can be imported."""
        try:
            from utils.api_client import APIClient
            assert APIClient is not None
        except ImportError as e:
            pytest.fail(f"Failed to import APIClient: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
