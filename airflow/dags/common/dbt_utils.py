"""
dbt Utilities for Airflow
Provides helper functions to run dbt commands in Airflow DAGs
"""
import os
import subprocess
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# dbt project paths
DBT_PROJECT_DIR = '/opt/airflow/dbt'
DBT_PROFILES_DIR = '/opt/airflow/dbt'

def check_dbt_installation() -> bool:
    """
    Check if dbt is installed and accessible
    
    Returns:
        bool: True if dbt is installed, False otherwise
    """
    try:
        result = subprocess.run(
            ['dbt', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            logger.info(f"✓ dbt is installed: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"✗ dbt check failed: {result.stderr}")
            return False
    except FileNotFoundError:
        logger.error("✗ dbt command not found - is dbt installed?")
        return False
    except Exception as e:
        logger.error(f"✗ Error checking dbt installation: {e}")
        return False

def run_dbt_command(
    command: str,
    models: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    full_refresh: bool = False,
    vars: Optional[Dict[str, str]] = None,
    target: Optional[str] = None
) -> Dict[str, any]:
    """
    Run a dbt command with specified options
    
    Args:
        command: dbt command to run ('run', 'test', 'snapshot', etc.)
        models: List of models to run (e.g., ['staging', 'marts.jobs'])
        exclude: List of models to exclude
        full_refresh: Whether to do full refresh (drop and recreate tables)
        vars: Dictionary of variables to pass to dbt
        target: Target environment (e.g., 'prod', 'dev')
    
    Returns:
        Dict with keys: success (bool), stdout (str), stderr (str), returncode (int)
    """
    # Build dbt command
    cmd = ['dbt', command]
    
    # Add project and profiles directory
    cmd.extend(['--project-dir', DBT_PROJECT_DIR])
    cmd.extend(['--profiles-dir', DBT_PROFILES_DIR])
    
    # Add model selection
    if models:
        for model in models:
            cmd.extend(['--select', model])
    
    # Add exclusions
    if exclude:
        for excl in exclude:
            cmd.extend(['--exclude', excl])
    
    # Add full refresh flag
    if full_refresh:
        cmd.append('--full-refresh')
    
    # Add variables
    if vars:
        vars_str = ' '.join([f'{k}:{v}' for k, v in vars.items()])
        cmd.extend(['--vars', f"'{vars_str}'"])
    
    # Add target
    if target:
        cmd.extend(['--target', target])
    
    logger.info(f"🔧 Running dbt command: {' '.join(cmd)}")
    
    try:
        # Run dbt command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout
            cwd=DBT_PROJECT_DIR
        )
        
        # Log output
        if result.stdout:
            logger.info(f"dbt stdout:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"dbt stderr:\n{result.stderr}")
        
        success = result.returncode == 0
        
        if success:
            logger.info(f"✓ dbt {command} completed successfully")
        else:
            logger.error(f"✗ dbt {command} failed with return code {result.returncode}")
        
        return {
            'success': success,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"✗ dbt {command} timed out after 30 minutes")
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Command timed out after 30 minutes',
            'returncode': -1
        }
    except Exception as e:
        logger.error(f"✗ Error running dbt {command}: {e}")
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def run_dbt_models(
    models: Optional[List[str]] = None,
    full_refresh: bool = False,
    target: str = 'prod'
) -> bool:
    """
    Run dbt models (simplified interface for common use case)
    
    Args:
        models: List of models to run (None = run all)
        full_refresh: Whether to do full refresh
        target: Target environment
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info("🚀 RUNNING DBT TRANSFORMATIONS")
    logger.info("=" * 80)
    
    # Check dbt installation
    if not check_dbt_installation():
        logger.error("✗ dbt is not installed - skipping transformations")
        return False
    
    # Run dbt models
    result = run_dbt_command(
        command='run',
        models=models,
        full_refresh=full_refresh,
        target=target
    )
    
    if result['success']:
        logger.info("\n✅ dbt transformations completed successfully")
        logger.info("=" * 80)
        return True
    else:
        logger.error("\n✗ dbt transformations failed")
        logger.error("=" * 80)
        return False

def run_dbt_tests(
    models: Optional[List[str]] = None,
    target: str = 'prod'
) -> bool:
    """
    Run dbt tests
    
    Args:
        models: List of models to test (None = test all)
        target: Target environment
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    logger.info("=" * 80)
    logger.info("🧪 RUNNING DBT TESTS")
    logger.info("=" * 80)
    
    result = run_dbt_command(
        command='test',
        models=models,
        target=target
    )
    
    if result['success']:
        logger.info("\n✅ All dbt tests passed")
        logger.info("=" * 80)
        return True
    else:
        logger.error("\n✗ Some dbt tests failed")
        logger.error("=" * 80)
        return False

def run_dbt_snapshot(target: str = 'prod') -> bool:
    """
    Run dbt snapshots
    
    Args:
        target: Target environment
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info("📸 RUNNING DBT SNAPSHOTS")
    logger.info("=" * 80)
    
    result = run_dbt_command(
        command='snapshot',
        target=target
    )
    
    if result['success']:
        logger.info("\n✅ dbt snapshots completed successfully")
        logger.info("=" * 80)
        return True
    else:
        logger.error("\n✗ dbt snapshots failed")
        logger.error("=" * 80)
        return False

def get_dbt_run_results() -> Optional[Dict]:
    """
    Parse and return dbt run results from run_results.json
    
    Returns:
        Dict with run results or None if not found
    """
    try:
        import json
        results_path = os.path.join(DBT_PROJECT_DIR, 'target', 'run_results.json')
        
        if not os.path.exists(results_path):
            logger.warning(f"dbt run results not found at {results_path}")
            return None
        
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        # Extract summary
        summary = {
            'elapsed_time': results.get('elapsed_time', 0),
            'success': results.get('results', []),
            'errors': [r for r in results.get('results', []) if r.get('status') == 'error'],
            'warnings': [r for r in results.get('results', []) if r.get('status') == 'warn'],
        }
        
        logger.info(f"\n📊 dbt Run Summary:")
        logger.info(f"   ✓ Elapsed time: {summary['elapsed_time']:.2f}s")
        logger.info(f"   ✓ Models run: {len(summary['success'])}")
        logger.info(f"   ✗ Errors: {len(summary['errors'])}")
        logger.info(f"   ⚠️  Warnings: {len(summary['warnings'])}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error reading dbt run results: {e}")
        return None
