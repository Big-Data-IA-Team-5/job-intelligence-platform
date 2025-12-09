#!/bin/bash

##############################################################################
# Production Deployment Script for Job Intelligence Platform
# This script handles the complete deployment process
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if .env file exists
check_env_file() {
    print_header "Checking Environment Configuration"
    
    if [ ! -f ".env" ]; then
        print_error ".env file not found!"
        print_info "Creating .env from template..."
        
        cat > .env << 'EOF'
# Airflow Configuration
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1

# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=JOB_INTELLIGENCE
SNOWFLAKE_SCHEMA=PROCESSED
SNOWFLAKE_ROLE=ACCOUNTADMIN

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key

# Airflow Project Directory
AIRFLOW_PROJ_DIR=./airflow
EOF
        
        print_warning "Please edit .env file with your credentials before continuing!"
        print_info "Run: nano .env"
        exit 1
    fi
    
    print_success ".env file found"
}

# Check system resources
check_system_resources() {
    print_header "Checking System Resources"
    
    # Check available memory
    if [ "$(uname)" == "Darwin" ]; then
        # macOS
        TOTAL_MEM=$(sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024)}')
    else
        # Linux
        TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
    fi
    
    print_info "Total Memory: ${TOTAL_MEM}GB"
    
    if [ "$TOTAL_MEM" -lt 16 ]; then
        print_warning "Less than 16GB RAM detected. Consider increasing Docker memory allocation."
        print_info "Recommended: At least 16GB for optimal performance"
    else
        print_success "Memory check passed"
    fi
    
    # Check CPU cores
    if [ "$(uname)" == "Darwin" ]; then
        CPU_CORES=$(sysctl -n hw.ncpu)
    else
        CPU_CORES=$(nproc)
    fi
    
    print_info "CPU Cores: ${CPU_CORES}"
    
    if [ "$CPU_CORES" -lt 4 ]; then
        print_warning "Less than 4 CPU cores detected. Performance may be limited."
    else
        print_success "CPU check passed"
    fi
}

# Check Docker
check_docker() {
    print_header "Checking Docker Installation"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        print_info "Please install Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    
    print_success "Docker is installed"
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running!"
        print_info "Please start Docker Desktop"
        exit 1
    fi
    
    print_success "Docker daemon is running"
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available!"
        exit 1
    fi
    
    print_success "Docker Compose is available"
    
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    print_info "Docker version: ${DOCKER_VERSION}"
}

# Create necessary directories
create_directories() {
    print_header "Creating Required Directories"
    
    directories=(
        "airflow/logs"
        "airflow/plugins"
        "airflow/scraped_jobs"
        "airflow/dags/__pycache__"
        "data"
        "logs"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created: $dir"
        else
            print_info "Exists: $dir"
        fi
    done
    
    # Set proper permissions
    if [ -d "airflow" ]; then
        chmod -R 777 airflow/logs airflow/plugins airflow/scraped_jobs 2>/dev/null || true
        print_success "Set permissions for Airflow directories"
    fi
}

# Build Docker images
build_images() {
    print_header "Building Docker Images"
    
    print_info "This may take several minutes..."
    
    if docker compose -f docker-compose.production.yml build --no-cache; then
        print_success "Docker images built successfully"
    else
        print_error "Failed to build Docker images"
        exit 1
    fi
}

# Start services
start_services() {
    print_header "Starting Services"
    
    print_info "Starting all containers..."
    
    if docker compose -f docker-compose.production.yml up -d; then
        print_success "Services started successfully"
    else
        print_error "Failed to start services"
        exit 1
    fi
    
    print_info "Waiting for services to be healthy..."
    sleep 30
}

# Check service health
check_health() {
    print_header "Checking Service Health"
    
    services=(
        "postgres:5432"
        "backend:8000"
        "frontend:8501"
        "selenium-chrome:4444"
        "airflow-webserver:8080"
    )
    
    for service in "${services[@]}"; do
        container="${service%%:*}"
        port="${service##*:}"
        
        if docker compose -f docker-compose.production.yml ps | grep -q "$container.*Up"; then
            print_success "$container is running"
            
            # Check if port is responding
            sleep 2
            if curl -f -s "http://localhost:$port/health" > /dev/null 2>&1 || \
               curl -f -s "http://localhost:$port" > /dev/null 2>&1; then
                print_success "$container is healthy on port $port"
            else
                print_warning "$container is running but may not be ready yet"
            fi
        else
            print_error "$container is not running"
        fi
    done
}

# Show service URLs
show_urls() {
    print_header "Service URLs"
    
    echo ""
    echo -e "${GREEN}Frontend (Streamlit):${NC}     http://localhost:8501"
    echo -e "${GREEN}Backend API:${NC}              http://localhost:8000"
    echo -e "${GREEN}API Docs:${NC}                 http://localhost:8000/docs"
    echo -e "${GREEN}Airflow UI:${NC}               http://localhost:8080"
    echo -e "${GREEN}Selenium Grid:${NC}            http://localhost:4444"
    echo -e "${GREEN}Selenium VNC:${NC}             http://localhost:7900 (password: secret)"
    echo ""
    
    print_info "Default Airflow credentials: airflow / airflow"
}

# Show logs
show_logs() {
    print_header "Recent Logs"
    
    print_info "Backend logs:"
    docker compose -f docker-compose.production.yml logs --tail=10 backend
    
    echo ""
    print_info "To follow all logs, run:"
    echo "  docker compose -f docker-compose.production.yml logs -f"
}

# Main deployment function
deploy() {
    clear
    
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     Job Intelligence Platform - Production Deployment    ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    check_env_file
    check_system_resources
    check_docker
    create_directories
    build_images
    start_services
    check_health
    show_urls
    show_logs
    
    print_header "Deployment Complete!"
    print_success "All services are running"
    
    echo ""
    print_info "Next steps:"
    echo "  1. Visit http://localhost:8501 for the frontend"
    echo "  2. Visit http://localhost:8080 for Airflow UI"
    echo "  3. Check logs: docker compose -f docker-compose.production.yml logs -f"
    echo "  4. Stop services: docker compose -f docker-compose.production.yml down"
    echo ""
}

# Handle script arguments
case "${1:-}" in
    "stop")
        print_header "Stopping Services"
        docker compose -f docker-compose.production.yml down
        print_success "Services stopped"
        ;;
    "restart")
        print_header "Restarting Services"
        docker compose -f docker-compose.production.yml restart
        print_success "Services restarted"
        ;;
    "logs")
        docker compose -f docker-compose.production.yml logs -f "${2:-}"
        ;;
    "status")
        print_header "Service Status"
        docker compose -f docker-compose.production.yml ps
        ;;
    "clean")
        print_header "Cleaning Up"
        docker compose -f docker-compose.production.yml down -v --remove-orphans
        print_success "Cleanup complete"
        ;;
    *)
        deploy
        ;;
esac
