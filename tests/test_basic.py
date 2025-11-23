"""Basic tests to ensure the project structure is valid."""
import pytest
from pathlib import Path


def test_project_structure():
    """Test that key directories exist."""
    project_root = Path(__file__).parent.parent
    
    assert (project_root / "backend").exists()
    assert (project_root / "frontend").exists()
    assert (project_root / "scrapers").exists()
    assert (project_root / "dbt").exists()
    assert (project_root / "snowflake").exists()


def test_requirements_files():
    """Test that requirements files exist."""
    project_root = Path(__file__).parent.parent
    
    assert (project_root / "requirements.txt").exists()
    assert (project_root / "backend" / "requirements.txt").exists()
    assert (project_root / "frontend" / "requirements.txt").exists()


def test_docker_files():
    """Test that Docker files exist."""
    project_root = Path(__file__).parent.parent
    
    assert (project_root / "docker-compose.yml").exists()
    assert (project_root / "backend" / "Dockerfile").exists()
    assert (project_root / "frontend" / "Dockerfile").exists()


def test_config_templates():
    """Test that configuration templates exist."""
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    
    assert (config_dir / "secrets.template").exists()
    assert (config_dir / "snowflake_config.template").exists()


def test_documentation():
    """Test that documentation files exist."""
    project_root = Path(__file__).parent.parent
    docs_dir = project_root / "docs"
    
    assert (project_root / "README.md").exists()
    assert (docs_dir / "architecture.md").exists()
    assert (docs_dir / "api_documentation.md").exists()
