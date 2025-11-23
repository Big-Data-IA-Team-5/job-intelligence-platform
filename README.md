# Job Intelligence Platform

A comprehensive job market intelligence platform that scrapes, processes, and analyzes job postings with H1B visa sponsorship matching, powered by Snowflake and Cortex AI.

## Features

- **Automated Job Collection**: Daily scraping of job postings using Apache Airflow
- **Data Processing Pipeline**: DBT-based transformation and enrichment
- **H1B Visa Matching**: Intelligent matching with H1B sponsorship data
- **Semantic Search**: Cortex-powered job search and classification
- **Resume Matching**: AI-driven resume-to-job matching
- **Analytics Dashboard**: Interactive Streamlit-based insights
- **RESTful API**: FastAPI backend for programmatic access

## Architecture

```
Job Scrapers → Snowflake (Raw) → DBT → Snowflake (Processed) → API/Frontend
     ↓                                ↓
  Airflow                      Cortex AI Agents
```

## Tech Stack

- **Orchestration**: Apache Airflow
- **Data Warehouse**: Snowflake
- **Transformation**: DBT
- **AI/ML**: Snowflake Cortex
- **Backend**: FastAPI (Python)
- **Frontend**: Streamlit
- **Containerization**: Docker

## Quick Start

### Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Snowflake Account
- OpenAI API Key (for embeddings)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd job-intelligence-platform
   ```

2. **Configure environment**
   ```bash
   cp config/.env.template config/.env
   cp config/snowflake_config.template config/snowflake_config.yml
   cp config/secrets.template config/secrets.yml
   # Edit the files with your credentials
   ```

3. **Run setup script**
   ```bash
   chmod +x scripts/setup_local.sh
   ./scripts/setup_local.sh
   ```

4. **Initialize Snowflake**
   ```bash
   # Execute SQL scripts in snowflake/setup/ in order
   ```

5. **Start services**
   ```bash
   docker-compose up -d
   ```

## Project Structure

- **airflow/**: Orchestration DAGs and plugins
- **scrapers/**: Job scraping logic
- **dbt/**: Data transformation models
- **snowflake/**: Database setup and AI agents
- **backend/**: FastAPI REST API
- **frontend/**: Streamlit web application
- **scripts/**: Utility and setup scripts
- **docs/**: Documentation

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run backend
cd backend
uvicorn app.main:app --reload

# Run frontend
cd frontend
streamlit run Home.py
```

### Testing

```bash
pytest tests/
```

## Deployment

See [Deployment Guide](docs/deployment_guide.md) for production deployment instructions.

## API Documentation

API documentation is available at `http://localhost:8000/docs` when running the backend.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

See [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please open an issue.
