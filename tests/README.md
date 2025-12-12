# Test Suite Documentation

## Overview
Comprehensive pytest test suite covering all platform components with proper markers and organization.

## Test Organization

### 1. **test_basic.py** - Basic Structure Validation
- ✅ Project structure validation
- ✅ Required files check
- ✅ Docker configuration check
- ✅ Documentation files check

**Run:** `pytest tests/test_basic.py -v`

---

### 2. **test_api_endpoints.py** - Backend REST API Testing
Complete API endpoint testing with real requests.

#### Test Classes:
- **TestJobSearchAPI** - Search functionality
  - Basic search
  - Location filtering
  - Company filtering
  - Date filtering
  - H-1B visa sponsorship filtering
  - Pagination (offset/limit)
  - Sorting options

- **TestFilterOptionsAPI** - Filter dropdown data
  - Companies list endpoint
  - Locations list endpoint

- **TestJobDetailsAPI** - Job detail endpoints
  - Get job by ID

- **TestAnalyticsAPI** - Analytics endpoints
  - Overall statistics
  - Company statistics
  - Location statistics

**Run:** `pytest tests/test_api_endpoints.py -v`
**Run (specific test):** `pytest tests/test_api_endpoints.py::TestJobSearchAPI::test_pagination -v`

---

### 3. **test_integration.py** - Snowflake Integration Testing
Tests database connectivity and data quality (marked as `@pytest.mark.integration`).

#### Test Classes:
- **TestSnowflakeConnection**
  - AgentManager singleton pattern
  - Database connection validation
  - Schema validation

- **TestJobsProcessedTable**
  - Table data existence
  - Required columns validation
  - Data quality checks

**Run:** `pytest tests/test_integration.py -v -m integration`

---

### 4. **test_agent2.py** - Agent 2 Chat Agent Testing
Tests the Job Intelligence Chat Agent with various query types.

#### Test Classes:
- **TestContactQueries** - Contact information lookups
- **TestSalaryQueries** - Salary information retrieval
- **TestSponsorshipQueries** - H-1B sponsorship info

**Run:** `pytest tests/test_agent2.py -v`

---

### 5. **test_agent2_comprehensive.py** - Extended Chat Agent Testing
Comprehensive testing of Agent 2 with more complex scenarios.

**Run:** `pytest tests/test_agent2_comprehensive.py -v`

---

### 6. **test_agent4.py** - Resume Matcher Agent Testing
Tests resume matching and similarity scoring.

**Run:** `pytest tests/test_agent4.py -v`

---

### 7. **test_all_systems.py** - End-to-End System Testing
Complete integration test of all agents and systems together.

**Run:** `pytest tests/test_all_systems.py -v`

---

### 8. **test_platform_demo.py** - Comprehensive Platform Demo
Full platform demonstration with visual output.

**Run:** `python tests/test_platform_demo.py`

---

### 9. **test_frontend.py** - Frontend Component Testing
Tests frontend utility modules and components.

**Run:** `pytest tests/test_frontend.py -v`

---

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Only Unit Tests
```bash
pytest tests/ -v -m unit
```

### Run Only Integration Tests
```bash
pytest tests/ -v -m integration
```

### Run Specific Test File
```bash
pytest tests/test_api_endpoints.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_api_endpoints.py::TestJobSearchAPI -v
```

### Run Specific Test
```bash
pytest tests/test_api_endpoints.py::TestJobSearchAPI::test_pagination -v
```

### Run with Coverage Report
```bash
pip install pytest-cov
pytest tests/ --cov=. --cov-report=html
```

### Run Tests Excluding Slow Tests
```bash
pytest tests/ -v -m "not slow"
```

---

## Test Configuration

Configuration is in `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --strict-markers --tb=short --disable-warnings
```

Available markers:
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.api` - API endpoint tests

---

## Environment Requirements

Tests require:
- Valid Snowflake credentials in environment
- Backend service running and accessible
- Python 3.9+
- pytest, requests, and other dependencies from `requirements.txt`

---

## CI/CD Integration

For automated testing in CI/CD pipeline:

```bash
# Install dependencies
pip install -r requirements.txt -r backend/requirements.txt

# Run all tests
pytest tests/ -v --tb=short

# Generate coverage report
pytest tests/ --cov=. --cov-report=xml
```

---

## Test Coverage Goals

| Component | Coverage | Status |
|-----------|----------|--------|
| API Endpoints | 85%+ | ✅ |
| Database Integration | 80%+ | ✅ |
| Agents (AI) | 75%+ | ✅ |
| Frontend Utils | 70%+ | ✅ |
| Data Validation | 90%+ | ✅ |

---

## Adding New Tests

1. Create test file in `/tests/test_<component>.py`
2. Import pytest and required modules
3. Create test class inheriting from nothing (pytest style)
4. Add `@pytest.mark.<type>` decorator
5. Name test functions `test_<action>`
6. Use assertions for validation
7. Run: `pytest tests/test_<component>.py -v`

Example:
```python
import pytest

@pytest.mark.unit
class TestMyFeature:
    def test_something_works(self):
        """Test description."""
        result = my_function()
        assert result == expected_value
```

---

## Troubleshooting

### Tests Fail with Connection Error
- Ensure backend service is running: `curl https://job-intelligence-backend-...`
- Check Snowflake credentials in environment
- Verify VPN/network access

### Import Errors
- Ensure `conftest.py` is in tests directory
- Check `sys.path` additions in conftest.py
- Run from project root: `pytest tests/ -v`

### Slow Tests
- Use `-m "not slow"` to skip slow tests
- Check database performance
- Consider reducing data size for development tests

---

## Test Results Summary Template

When running tests, you should see output like:

```
============================= test session starts ==============================
collected 45 items

tests/test_basic.py .....                                                [ 11%]
tests/test_api_endpoints.py .................                             [ 48%]
tests/test_integration.py ......                                          [ 61%]
tests/test_agent2.py ...........                                          [ 85%]
tests/test_frontend.py ..                                                 [100%]

============================== 45 passed in 12.34s ==============================
```

---

**Last Updated:** December 12, 2025  
**Maintained By:** Job Intelligence Platform Team
