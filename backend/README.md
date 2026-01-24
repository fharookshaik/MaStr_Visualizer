# MaStR Visualizer Backend

A FastAPI-based backend service for visualizing German energy market data (MaStR - Marktstammdatenregister). This service provides RESTful APIs to access and query renewable energy infrastructure data from the German Federal Network Agency.

## Features

- **FastAPI REST API**: High-performance asynchronous API endpoints
- **PostgreSQL Integration**: Robust database operations with connection pooling
- **Automatic Data Population**: Smart database initialization that downloads and processes MaStR data on first run
- **GeoJSON Output**: Standardized geospatial data format for mapping applications
- **Comprehensive Logging**: Configurable logging system with multiple verbosity levels
- **Docker Support**: Containerized deployment with docker-compose
- **MaStR Integration**: Direct integration with German energy market registry data

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   PostgreSQL    │    │   MaStR Data    │
│                 │    │   Database      │    │   (Bundesnetz-  │
│ • REST Endpoints│◄──►│ • Wind turbines │    │    agentur)     │
│ • GeoJSON API   │    │ • Solar panels  │    │                 │
│ • Health checks │    │ • Other RE units│    │ • XML Downloads │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       ▲                       │
         └───────────────────────┼───────────────────────┘
                         Auto-population
                     (runs on first startup)
```

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 13+ (for local development)
- Git

## Quick Start with Docker

1. **Clone and navigate to the project:**
   ```bash
   cd /path/to/MaStR_Visualizer
   ```

2. **Start the services:**
   ```bash
   docker-compose up --build
   ```

   This will:
   - Start PostgreSQL database
   - Build and start the FastAPI backend
   - Automatically populate the database with MaStR wind turbine data (first run only)

3. **Access the API:**
   - API Documentation: http://localhost:8000/docs
   - Alternative Docs: http://localhost:8000/redoc

## API Endpoints

### GET `/api/tables`
Returns a list of all available database tables.

**Response:**
```json
{
  "tables": [
    {"table_name": "wind_extended"},
    {"table_name": "solar_extended"},
    ...
  ]
}
```

### GET `/api/units`
Returns geojson features for energy units with optional filtering.

**Parameters:**
- `unit_type` (required): Type of energy unit (`wind`, `solar`, `storage`, `biomass`, `hydro`, `combustion`, `nuclear`)
- `min_lat`, `min_lon`, `max_lat`, `max_lon` (optional): Bounding box coordinates
- `limit` (optional): Maximum number of results (default: 5000)

**Example:**
```bash
curl "http://localhost:8000/api/units?unit_type=wind&limit=100"
```

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [10.123, 52.456]
      },
      "properties": {
        "unit_type": "wind",
        "EinheitMastrNummer": "SEE123456789",
        "Name": "Windpark Example",
        ...
      }
    }
  ]
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `db` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `mastr_db` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `1234` | Database password |
| `DB_SCHEMA` | `public` | Database schema |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

### Database Tables

The system creates and populates the following tables:

- `wind_extended` - Wind turbines
- `solar_extended` - Solar installations
- `storage_extended` - Energy storage systems
- `biomass_extended` - Biomass plants
- `hydro_extended` - Hydroelectric plants
- `combustion_extended` - Fossil fuel plants
- `nuclear_extended` - Nuclear plants

## Local Development

### Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

4. **Start PostgreSQL:**
   ```bash
   # Using Docker for local DB
   docker run -d --name postgres-mastr \
     -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=1234 \
     -e POSTGRES_DB=mastr_db \
     -p 5432:5432 postgres:18
   ```

5. **Populate database (optional):**
   ```bash
   python mastr_orchestrator.py
   ```

6. **Run the application:**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

### Manual Database Population

To populate the database manually:

```bash
python mastr_orchestrator.py
```

This script will:
1. Download the latest MaStR data (ZIP file)
2. Extract and process XML data
3. Insert wind turbine data into PostgreSQL
4. Create necessary indexes

**Note:** First run downloads ~500MB of data and may take 10-30 minutes depending on your internet connection.

## Project Structure

```
backend/
├── app.py                 # FastAPI application and routes
├── init_db.py            # Database initialization script
├── mastr_orchestrator.py # MaStR data download and processing
├── logger.py             # Centralized logging configuration
├── utils.py              # Database utilities and configuration
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container build instructions
├── mastr_lite/          # MaStR data processing library
│   ├── main.py
│   └── utils/
│       ├── db.py
│       ├── download_mastr.py
│       ├── orm.py
│       └── ...
└── .env                 # Environment configuration
```

## Data Sources

- **MaStR Database**: Official German energy market registry maintained by Bundesnetzagentur
- **Data Updates**: MaStR data is updated regularly. The orchestrator downloads the latest available dataset
- **Coverage**: Germany-wide renewable energy infrastructure data
- **License**: Data is publicly available under German open data policies

## Monitoring and Logs

### Log Levels

Set the desired log level via `LOG_LEVEL` environment variable:

- `DEBUG`: Detailed debugging information
- `INFO`: General information about application operation
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors that may cause application shutdown

### Docker Logs

```bash
# View backend logs
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f backend

# View database logs
docker-compose logs db
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Ensure PostgreSQL is running and accessible
   - Check environment variables in `.env`
   - Verify database credentials

2. **No Data Returned**
   - Check if database population completed successfully
   - Verify table names and unit types
   - Check API logs for errors

3. **Slow API Responses**
   - Database may need indexes
   - Check PostgreSQL performance
   - Consider reducing result limits

4. **Memory Issues During Population**
   - MaStR data processing is memory-intensive
   - Ensure sufficient RAM (8GB+ recommended)
   - Process can be restarted if interrupted

### Database Maintenance

```sql
-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Reindex tables (if needed)
REINDEX TABLE wind_extended;
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please check the main project license for details.

## Support

For issues and questions:
1. Check the logs for error messages
2. Verify your environment configuration
3. Review the API documentation at `/docs`
4. Check existing issues in the project repository
