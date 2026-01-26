# Deployment Guide

This guide provides comprehensive instructions for deploying the MaStr Visualizer in various environments, from local development to production.

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL2
- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Memory**: Minimum 8GB RAM (16GB recommended for optimal performance)
- **Storage**: Minimum 2GB free space (5GB recommended for data processing)
- **Network**: Internet connection for initial data download

### Software Dependencies

- Docker Engine
- Docker Compose
- Git (for cloning the repository)

## Quick Start Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/fharookshaik/MaStr_Visualizer.git
cd MaStr_Visualizer
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit the environment variables if needed
nano .env
```

**Important**: The default configuration is suitable for development. For production, consider changing database passwords and other sensitive information.

### 3. Start the Application

```bash
# Build and start all services
docker-compose up --build
```

**First Run Note**: The initial startup will automatically download and process ~500MB of MaStR data, which may take 10-30 minutes depending on your internet connection.

### 4. Access the Application

Once all services are running:

- **Frontend Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## Docker Architecture

The deployment uses a three-tier Docker architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Streamlit)                 │
│                    Port: 8501                           │
│                    Image: mastr-frontend                │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                    │
│                    Port: 8000                           │
│                    Image: mastr-backend                 │
│                    Health Check: /docs                  │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                    Database (PostgreSQL)                │
│                    Port: 5433 (external)                │
│                    Image: postgis/postgis:18-3.6-alpine │
│                    Health Check: pg_isready             │
└─────────────────────────────────────────────────────────┘
```

## Environment Configuration

### Environment Variables

Create or modify the `.env` file with the following variables:

```bash
# Database Configuration
DB_HOST=db
DB_PORT=5432
DB_NAME=mastr_db
DB_USER=postgres
DB_PASSWORD=your_secure_password_here
DB_SCHEMA=public

# Application Configuration
LOG_LEVEL=INFO

# Frontend Configuration
BACKEND_URL=http://backend:8000
MAP_BACKEND_URL=http://localhost:8000
```

### Production Environment Variables

For production deployments, consider these additional configurations:

```bash
# Database Security
DB_PASSWORD=your_very_secure_password_here
POSTGRES_INITDB_ARGS="--auth-host=scram-sha-256"

# Application Security
LOG_LEVEL=WARNING
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]

# Performance Tuning
DB_POOL_MIN_SIZE=10
DB_POOL_MAX_SIZE=20
```

## Service Management

### Starting Services

```bash
# Start all services in the background
docker-compose up -d

# Start specific service
docker-compose up -d backend

# Start with logs
docker-compose up backend
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop specific service
docker-compose stop backend

# Stop and remove containers
docker-compose down --remove-orphans
```

### Monitoring Services

```bash
# View logs
docker-compose logs
docker-compose logs backend
docker-compose logs -f  # Follow logs

# Check service status
docker-compose ps

# View resource usage
docker stats
```

### Service Health Checks

Each service includes health checks:

```bash
# Check database health
docker-compose exec db pg_isready -U postgres

# Check backend health
curl http://localhost:8000/docs

# Check frontend health
curl http://localhost:8501/_stcore/health
```

## Data Management

### Initial Data Population

The system automatically populates the database on first startup:

1. **Automatic Download**: Downloads latest MaStR XML data (~500MB)
2. **Processing**: Parses and processes XML data
3. **Loading**: Bulk loads data into PostgreSQL
4. **Indexing**: Creates spatial and performance indexes

### Manual Data Updates

To manually update data:

```bash
# Access the backend container
docker-compose exec backend bash

# Run the data update script
python mastr_orchestrator.py
```

### Database Backups

```bash
# Create backup
docker-compose exec db pg_dump -U postgres mastr_db > backup_$(date +%Y%m%d).sql

# Restore from backup
docker-compose exec -T db psql -U postgres -d mastr_db < backup_file.sql
```

### Data Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect MaStr_Visualizer_db

# Backup volume
docker run --rm -v MaStr_Visualizer_db:/data -v $(pwd):/backup busybox tar czf /backup/db_backup.tar.gz /data
```

## Production Deployment

### 1. Security Hardening

#### Network Security
```bash
# Use Docker networks with explicit allow rules
docker network create --driver bridge mastr_network

# Update docker-compose.yml to use custom network
networks:
  default:
    name: mastr_network
```

#### Database Security
```bash
# Change default passwords
DB_PASSWORD=your_very_secure_password_here

# Enable SSL (requires SSL certificates)
POSTGRES_INITDB_ARGS="--auth-host=scram-sha-256 --ssl"

# Restrict database access
PG_HBA_CONF="host all all 0.0.0.0/0 md5"
```

#### Application Security
```bash
# Enable CORS restrictions
CORS_ORIGINS=["https://yourdomain.com"]

# Add authentication middleware
# (Implementation depends on your authentication requirements)
```

### 2. Performance Optimization

#### Database Tuning
```bash
# Increase shared buffers
POSTGRES_SHARED_BUFFERS=256MB

# Optimize work memory
POSTGRES_WORK_MEM=16MB

# Configure maintenance work memory
POSTGRES_MAINTENANCE_WORK_MEM=64MB
```

#### Application Tuning
```bash
# Increase worker processes
UVICORN_WORKERS=4

# Enable request logging
LOG_LEVEL=INFO

# Configure connection pooling
DB_POOL_MIN_SIZE=10
DB_POOL_MAX_SIZE=20
```

#### Frontend Optimization
```bash
# Enable caching
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
STREAMLIT_SERVER_ENABLE_CORS=false
```

### 3. Load Balancing and Scaling

#### Horizontal Scaling
```bash
# Scale backend services
docker-compose up -d --scale backend=3

# Use external load balancer (e.g., NGINX, Traefik)
# Configure load balancing across multiple backend instances
```

#### Caching Strategy
```bash
# Add Redis for caching
# Update docker-compose.yml to include Redis service
# Configure FastAPI to use Redis for response caching
```

### 4. Monitoring and Logging

#### Application Monitoring
```bash
# Add health check endpoints
# Implement metrics collection (Prometheus, Grafana)
# Set up alerting for critical issues
```

#### Log Management
```bash
# Centralize logs
docker-compose logs --tail=100 --follow > application.log

# Use log aggregation (ELK Stack, Fluentd)
# Configure log rotation
```

## Cloud Deployment

### AWS Deployment

#### Using ECS (Elastic Container Service)
```yaml
# Create task definition
# Configure ECS service with desired count
# Set up Application Load Balancer
# Configure RDS PostgreSQL instance
```

#### Using EKS (Elastic Kubernetes Service)
```yaml
# Create Kubernetes manifests
# Deploy to EKS cluster
# Configure RDS PostgreSQL
# Set up Ingress controller
```

### Azure Deployment

#### Using AKS (Azure Kubernetes Service)
```yaml
# Create AKS cluster
# Deploy application using Helm charts
# Configure Azure Database for PostgreSQL
# Set up Azure Application Gateway
```

### Google Cloud Deployment

#### Using GKE (Google Kubernetes Engine)
```yaml
# Create GKE cluster
# Deploy application
# Configure Cloud SQL PostgreSQL
# Set up Cloud Load Balancer
```

## Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database service
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec backend python -c "import psycopg2; conn = psycopg2.connect('dbname=mastr_db user=postgres password=1234 host=db'); print('Connected')"
```

#### Backend Service Issues
```bash
# Check backend logs
docker-compose logs backend

# Test API endpoints
curl http://localhost:8000/docs

# Check Python dependencies
docker-compose exec backend pip list
```

#### Frontend Issues
```bash
# Check frontend logs
docker-compose logs frontend

# Test frontend access
curl http://localhost:8501

# Check Streamlit configuration
docker-compose exec frontend streamlit config show
```

### Performance Issues

#### Slow Vector Tile Rendering
```bash
# Check spatial indexes
docker-compose exec db psql -U postgres -d mastr_db -c "SELECT indexname, tablename FROM pg_indexes WHERE tablename LIKE '%extended%'"

# Monitor query performance
docker-compose exec db psql -U postgres -d mastr_db -c "EXPLAIN ANALYZE SELECT COUNT(*) FROM wind_extended WHERE geom && ST_Transform(ST_TileEnvelope(10, 546, 350), 4326)"
```

#### High Memory Usage
```bash
# Monitor memory usage
docker stats

# Check for memory leaks
docker-compose exec backend python -c "import psutil; print(f'Memory usage: {psutil.Process().memory_info().rss / 1024 / 1024} MB')"
```

## Maintenance

### Regular Tasks

#### Database Maintenance
```bash
# Vacuum and analyze tables
docker-compose exec db psql -U postgres -d mastr_db -c "VACUUM ANALYZE;"

# Update statistics
docker-compose exec db psql -U postgres -d mastr_db -c "ANALYZE;"

# Reindex if needed
docker-compose exec db psql -U postgres -d mastr_db -c "REINDEX TABLE wind_extended;"
```

---
This deployment guide provides comprehensive instructions for deploying MaStr Visualizer in various environments. Always test deployments in a staging environment before production.