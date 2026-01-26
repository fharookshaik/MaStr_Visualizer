# Troubleshooting Guide

This guide provides solutions for common issues, error messages, and maintenance procedures for the MaStr Visualizer project.

## Table of Contents

- [Common Issues](#common-issues)
- [Docker Problems](#docker-problems)
- [Database Issues](#database-issues)
- [Backend Problems](#backend-problems)
- [Frontend Issues](#frontend-issues)
- [Performance Problems](#performance-problems)
- [Data Processing Issues](#data-processing-issues)
- [Network and Connectivity](#network-and-connectivity)
- [Maintenance Procedures](#maintenance-procedures)
- [Debugging Tools](#debugging-tools)

## Common Issues

### Application Won't Start

**Symptoms**: Docker containers fail to start or crash immediately.

**Solutions**:

1. **Check Docker Installation**:
   ```bash
   docker --version
   docker-compose --version
   ```

2. **Verify System Resources**:
   ```bash
   # Check available memory
   free -h
   
   # Check disk space
   df -h
   
   # Check Docker disk usage
   docker system df
   ```

3. **Clean Docker Resources**:
   ```bash
   # Remove unused containers, networks, and images
   docker system prune -a
   
   # Remove all Docker data (use with caution)
   docker system prune -a --volumes
   ```

4. **Check Port Conflicts**:
   ```bash
   # Check if ports are in use
   lsof -i :8000
   lsof -i :8501
   lsof -i :5433
   ```

### First Startup Takes Too Long

**Symptoms**: Initial startup takes 30+ minutes or seems stuck.

**Solutions**:

1. **Monitor Progress**:
   ```bash
   # Check logs for progress
   docker-compose logs -f backend
   
   # Look for download progress indicators
   ```

2. **Check Internet Connection**:
   ```bash
   # Test connection to MaStR source
   curl -I https://www.marktstammdatenregister.de/
   ```

3. **Verify Disk Space**:
   ```bash
   # Ensure sufficient space for data processing
   df -h
   ```

4. **Patience**: Initial data download and processing can take 10-30 minutes depending on internet speed.

## Docker Problems

### Container Won't Build

**Error**: `docker-compose up --build` fails during build process.

**Solutions**:

1. **Check Dockerfile Syntax**:
   ```bash
   # Validate Dockerfile
   docker build --dry-run -f backend/Dockerfile .
   ```

2. **Clear Build Cache**:
   ```bash
   # Remove build cache
   docker builder prune
   
   # Rebuild with no cache
   docker-compose build --no-cache
   ```

3. **Check Dependencies**:
   ```bash
   # Verify requirements.txt files exist
   ls backend/requirements.txt
   ls frontend/requirements.txt
   ```

4. **Network Issues**:
   ```bash
   # Check Docker network connectivity
   docker run --rm alpine ping -c 3 google.com
   ```

### Container Crashes on Startup

**Error**: Container starts then immediately exits.

**Solutions**:

1. **Check Logs**:
   ```bash
   docker-compose logs backend
   docker-compose logs frontend
   docker-compose logs db
   ```

2. **Environment Variables**:
   ```bash
   # Verify .env file exists and has correct values
   cat .env
   
   # Check for missing environment variables
   docker-compose exec backend env | grep DB_
   ```

3. **Database Connection**:
   ```bash
   # Check if database is ready
   docker-compose exec db pg_isready -U postgres
   
   # Test database connection from backend
   docker-compose exec backend python -c "
   import psycopg2
   conn = psycopg2.connect('dbname=mastr_db user=postgres password=1234 host=db')
   print('Connected successfully')
   "
   ```

### Volume Permission Issues

**Error**: Permission denied when accessing mounted volumes.

**Solutions**:

1. **Check Volume Ownership**:
   ```bash
   # Check volume permissions
   docker-compose exec backend ls -la /app
   
   # Fix permissions
   docker-compose exec backend chown -R 1000:1000 /app
   ```

2. **Recreate Volumes**:
   ```bash
   # Remove and recreate volumes
   docker-compose down -v
   docker-compose up -d
   ```

## Database Issues

### Database Won't Start

**Error**: PostgreSQL container fails to start.

**Solutions**:

1. **Check Logs**:
   ```bash
   docker-compose logs db
   ```

2. **Volume Conflicts**:
   ```bash
   # Remove conflicting volumes
   docker volume rm MaStr_Visualizer_db
   docker-compose up -d db
   ```

3. **Port Conflicts**:
   ```bash
   # Check if port 5432/5433 is in use
   sudo lsof -i :5432
   sudo lsof -i :5433
   
   # Stop conflicting services
   sudo systemctl stop postgresql  # If running local PostgreSQL
   ```

4. **Memory Issues**:
   ```bash
   # Check available memory
   free -h
   
   # PostgreSQL needs at least 256MB for basic operation
   ```

### Database Connection Errors

**Error**: "Connection refused" or "Database not found".

**Solutions**:

1. **Check Database Status**:
   ```bash
   docker-compose ps db
   docker-compose exec db pg_isready -U postgres
   ```

2. **Verify Connection Details**:
   ```bash
   # Check environment variables
   docker-compose exec backend env | grep DB_
   
   # Test connection manually, Adapt actual database configuration
   docker-compose exec backend python -c "
   import os
   from mastr_lite.utils import DBConfig
   config = DBConfig(
       DB_HOST='db',
       DB_PORT=5432,
       DB_NAME='mastr_db',
       DB_USER='postgres',
       DB_PASSWORD='1234',
       DB_SCHEMA='public'
   )
   print('Config:', config.get_dsn())
   "
   ```

3. **Check Database Initialization**:
   ```bash
   # Check if database was created
   docker-compose exec db psql -U postgres -c "SELECT datname FROM pg_database;"
   
   # Check if tables exist
   docker-compose exec db psql -U postgres -d mastr_db -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
   ```

### Slow Database Queries

**Symptoms**: API responses are slow, especially for vector tiles.

**Solutions**:

1. **Check Indexes**:
   ```bash
   # Check if spatial indexes exist
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT indexname, tablename 
   FROM pg_indexes 
   WHERE tablename LIKE '%extended%'
   "
   ```

2. **Monitor Query Performance**:
   ```bash
   # Enable query logging
   docker-compose exec db psql -U postgres -d mastr_db -c "
   ALTER SYSTEM SET log_min_duration_statement = 1000;
   SELECT pg_reload_conf();
   "
   
   # Check slow queries
   docker-compose logs db | grep "duration:"
   ```

3. **Database Tuning**:
   ```bash
   # Check current settings
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SHOW shared_buffers;
   SHOW work_mem;
   SHOW maintenance_work_mem;
   "
   ```

## Backend Problems

### API Endpoints Return Errors

**Error**: HTTP 500 errors or empty responses.

**Solutions**:

1. **Check Backend Logs**:
   ```bash
   docker-compose logs backend
   docker-compose logs -f backend  # Follow logs
   ```

2. **Test API Endpoints**:
   ```bash
   # Test basic endpoint
   curl http://localhost:8000/docs
   
   # Test specific endpoints
   curl http://localhost:8000/api/metadata/wind
   curl http://localhost:8000/api/stats?unit_type=wind
   ```

3. **Check Dependencies**:
   ```bash
   # Verify Python packages
   docker-compose exec backend pip list
   
   # Check for missing imports
   docker-compose exec backend python -c "import fastapi; import asyncpg; print('All imports OK')"
   ```

### Vector Tiles Not Loading

**Error**: Map shows blank or tiles fail to load.

**Solutions**:

1. **Test Tile Endpoint**:
   ```bash
   # Test tile endpoint directly
   curl -I "http://localhost:8000/api/tiles/wind/10/546/350"
   
   # Check response size
   curl -s "http://localhost:8000/api/tiles/wind/10/546/350" | wc -c
   ```

2. **Check Spatial Data**:
   ```bash
   # Verify spatial data exists
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT COUNT(*) FROM wind_extended WHERE geom IS NOT NULL;
   "
   
   # Check spatial index
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT indexname FROM pg_indexes WHERE indexname LIKE '%geom%';
   "
   ```

3. **Test Spatial Queries**:
   ```bash
   # Test tile query manually
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT COUNT(*) FROM wind_extended 
   WHERE geom && ST_Transform(ST_TileEnvelope(10, 546, 350), 4326);
   "
   ```

### Analytics Data Missing

**Error**: Charts show no data or error messages.

**Solutions**:

1. **Check Data Population**:
   ```bash
   # Verify data exists in tables
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT COUNT(*) FROM wind_extended;
   SELECT COUNT(*) FROM solar_extended;
   "
   
   # Check data quality
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT COUNT(*) FROM wind_extended WHERE Bruttoleistung > 0;
   "
   ```

2. **Test Analytics Endpoint**:
   ```bash
   # Test analytics API
   curl "http://localhost:8000/api/stats/advanced/wind"
   ```

3. **Check Processing Logs**:
   ```bash
   # Look for data processing errors
   docker-compose logs backend | grep -i "error\|fail\|exception"
   ```

## Frontend Issues

### Streamlit App Won't Load

**Error**: Frontend shows error or blank page.

**Solutions**:

1. **Check Frontend Logs**:
   ```bash
   docker-compose logs frontend
   ```

2. **Test Frontend Access**:
   ```bash
   # Test direct access
   curl http://localhost:8501
   
   # Check if Streamlit is running
   docker-compose exec frontend ps aux | grep streamlit
   ```

3. **Verify Backend Connection**:
   ```bash
   # Test API connectivity from frontend
   docker-compose exec frontend curl http://backend:8000/docs
   ```

### Map Not Displaying

**Error**: Map shows blank or error messages.

**Solutions**:

1. **Check Map Tiles**:
   ```bash
   # Test tile URL
   curl -I "http://localhost:8000/api/tiles/wind/10/546/350"
   ```

2. **Verify PyDeck**:
   ```bash
   # Check PyDeck installation
   docker-compose exec frontend python -c "import pydeck; print('PyDeck OK')"
   ```

3. **Check CORS Settings**:
   ```bash
   # Verify CORS configuration in backend
   docker-compose exec backend python -c "
   from fastapi.middleware.cors import CORSMiddleware
   print('CORS enabled')
   "
   ```

### Charts Not Loading

**Error**: Analytics charts show errors or don't render.

**Solutions**:

1. **Check Plotly**:
   ```bash
   # Verify Plotly installation
   docker-compose exec frontend python -c "import plotly; print('Plotly OK')"
   ```

2. **Test Data Fetching**:
   ```bash
   # Test data API calls
   docker-compose exec frontend python -c "
   import requests
   response = requests.get('http://backend:8000/api/stats/advanced/wind')
   print('Status:', response.status_code)
   print('Data length:', len(response.text))
   "
   ```

## Performance Problems

### Slow Application Response

**Symptoms**: Pages load slowly, interactions are laggy.

**Solutions**:

1. **Monitor Resource Usage**:
   ```bash
   # Check Docker resource usage
   docker stats
   
   # Check system resources
   top
   htop  # if available
   ```

2. **Database Performance**:
   ```bash
   # Check slow queries
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   "
   
   # Check index usage
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT indexname, idx_tup_read, idx_tup_fetch 
   FROM pg_stat_user_indexes 
   WHERE tablename LIKE '%extended%';
   "
   ```

3. **Application Caching**:
   ```bash
   # Check Streamlit cache
   docker-compose exec frontend streamlit cache list
   
   # Clear cache if needed
   docker-compose exec frontend streamlit cache clear
   ```

### High Memory Usage

**Symptoms**: System runs out of memory, containers crash.

**Solutions**:

1. **Monitor Memory**:
   ```bash
   # Check memory usage
   docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
   ```

2. **Optimize Docker Configuration**:
   ```bash
   # Limit container memory
   # Add to docker-compose.yml
   # services:
   #   backend:
   #     deploy:
   #       resources:
   #         limits:
   #           memory: 2G
   ```

3. **Database Memory Settings**:
   ```bash
   # Adjust PostgreSQL memory settings
   # Add to docker-compose.yml environment
   # POSTGRES_SHARED_BUFFERS=256MB
   # POSTGRES_WORK_MEM=16MB
   ```

### Slow Data Processing

**Symptoms**: Data updates take too long.

**Solutions**:

1. **Check Processing Logs**:
   ```bash
   # Monitor processing progress
   docker-compose logs -f backend | grep -i "processing\|download\|insert"
   ```

2. **Optimize Processing**:
   ```bash
   # Process smaller batches
   # Modify mastr_orchestrator.py settings
   ```

3. **Database Optimization**:
   ```bash
   # Update table statistics
   docker-compose exec db psql -U postgres -d mastr_db -c "ANALYZE;"
   
   # Reindex if needed
   docker-compose exec db psql -U postgres -d mastr_db -c "REINDEX TABLE wind_extended;"
   ```

## Data Processing Issues

### Download Failures

**Error**: MaStR data download fails or times out.

**Solutions**:

1. **Check Internet Connection**:
   ```bash
   # Test connectivity
   curl -I https://www.marktstammdatenregister.de/
   
   # Check download directory
   ls -la /path/to/downloads
   ```

2. **Manual Download**:
   ```bash
   # Download manually from browser
   # Place in downloads directory
   # Run processing script manually
   ```

3. **Retry Mechanism**:
   ```bash
   # Implement retry logic
   # Check mastr_lite download_mastr.py for retry settings
   ```

### Processing Errors

**Error**: XML processing fails or produces incorrect data.

**Solutions**:

1. **Check XML Integrity**:
   ```bash
   # Verify downloaded file
   file /path/to/mastr_data.zip
   
   # Check file size
   ls -lh /path/to/mastr_data.zip
   ```

2. **Manual Processing**:
   ```bash
   # Run processing manually
   docker-compose exec backend python mastr_orchestrator.py
   ```

3. **Data Validation**:
   ```bash
   # Check processed data
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT COUNT(*) FROM wind_extended;
   SELECT COUNT(*) FROM wind_extended WHERE geom IS NULL;
   "
   ```

### Data Quality Issues

**Error**: Data contains errors or inconsistencies.

**Solutions**:

1. **Data Validation**:
   ```bash
   # Check for null values
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT COUNT(*) FROM wind_extended WHERE geom IS NULL;
   SELECT COUNT(*) FROM wind_extended WHERE Bruttoleistung <= 0;
   "
   
   # Check coordinate validity
   docker-compose exec db psql -U postgres -d mastr_db -c "
   SELECT COUNT(*) FROM wind_extended 
   WHERE ST_X(geom) < -180 OR ST_X(geom) > 180 
   OR ST_Y(geom) < -90 OR ST_Y(geom) > 90;
   "
   ```

2. **Data Cleansing**:
   ```bash
   # Run data cleansing
   docker-compose exec backend python -c "
   from mastr_lite.utils import DBHelper
   from mastr_lite.utils import DBConfig
   config = DBConfig(...)
   db_helper = DBHelper(db_config=config)
   db_helper.run_data_cleansing()
   "
   ```

## Network and Connectivity

### CORS Errors

**Error**: Cross-origin resource sharing errors in browser.

**Solutions**:

1. **Check CORS Configuration**:
   ```bash
   # Verify backend CORS settings
   docker-compose exec backend python -c "
   from fastapi.middleware.cors import CORSMiddleware
   print('CORS enabled')
   "
   ```

2. **Update CORS Settings**:
   ```python
   # In backend/app.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:8501"],  # Add specific origins
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

### Port Conflicts

**Error**: Ports already in use by other services.

**Solutions**:

1. **Find Conflicting Services**:
   ```bash
   # Check port usage
   sudo lsof -i :8000
   sudo lsof -i :8501
   sudo lsof -i :5433
   ```

2. **Change Ports**:
   ```yaml
   # In docker-compose.yml
   services:
     backend:
       ports:
         - "8001:8000"  # Change to different port
     frontend:
       ports:
         - "8502:8501"  # Change to different port
   ```

3. **Stop Conflicting Services**:
   ```bash
   # Stop other services using the ports
   sudo systemctl stop service_name
   ```

## Maintenance Procedures

### Regular Database Maintenance

```bash
# Vacuum and analyze tables
docker-compose exec db psql -U postgres -d mastr_db -c "VACUUM ANALYZE;"

# Update statistics
docker-compose exec db psql -U postgres -d mastr_db -c "ANALYZE;"

# Check index usage
docker-compose exec db psql -U postgres -d mastr_db -c "
SELECT indexname, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE tablename LIKE '%extended%';
"
```

### Application Updates

```bash
# Pull latest images
docker-compose pull

# Update services
docker-compose up -d

# Clean up old images
docker image prune

# Update dependencies
docker-compose build --no-cache
```

### Data Backup and Restore

```bash
# Create backup
docker-compose exec db pg_dump -U postgres mastr_db > backup_$(date +%Y%m%d).sql

# Restore from backup
docker-compose exec -T db psql -U postgres -d mastr_db < backup_file.sql

# Backup data files
tar -czf data_backup_$(date +%Y%m%d).tar.gz /path/to/data/files
```

### Log Management

```bash
# View logs
docker-compose logs --tail=100

# Follow logs
docker-compose logs -f

# Save logs to file
docker-compose logs --tail=1000 > application.log

# Clear logs
docker-compose logs --clear
```

## Debugging Tools

### Docker Debugging

```bash
# Check container status
docker-compose ps

# Inspect container
docker inspect container_name

# Execute commands in container
docker-compose exec container_name command

# View container details
docker-compose exec container_name env
docker-compose exec container_name ps aux
```

### Database Debugging

```bash
# Interactive PostgreSQL session
docker-compose exec db psql -U postgres -d mastr_db

# Check database size
docker-compose exec db psql -U postgres -d mastr_db -c "
SELECT pg_size_pretty(pg_total_relation_size('wind_extended'));
"

# Monitor active connections
docker-compose exec db psql -U postgres -d mastr_db -c "
SELECT * FROM pg_stat_activity WHERE datname = 'mastr_db';
"
```

### Application Debugging

```bash
# Check Python environment
docker-compose exec backend python --version
docker-compose exec backend pip list

# Test imports
docker-compose exec backend python -c "
import fastapi
import asyncpg
import psycopg2
print('All imports successful')
"

# Check configuration
docker-compose exec backend python -c "
from mastr_lite.utils import DBConfig
config = DBConfigenv()
print('Database config:', config.get_dsn())
"
```

### Performance Monitoring

```bash
# Monitor Docker resources
docker stats

# Check system resources
top
free -h
df -h

# Monitor network
netstat -tulpn | grep :8000
netstat -tulpn | grep :8501
```

This troubleshooting guide provides comprehensive solutions for maintaining and debugging the MaStr Visualizer application. Always check logs first when encountering issues, and consider the interdependencies between Docker containers, database, and application components.