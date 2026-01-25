# MaStR Visualizer Backend

A high-performance FastAPI-based backend service for visualizing German energy market data (MaStR - Marktstammdatenregister). This service provides RESTful APIs, vector tiles, and advanced analytics for renewable energy infrastructure data from the German Federal Network Agency.

## 🚀 Features

- **FastAPI REST API**: High-performance asynchronous API endpoints
- **Vector Tile Service**: High-frequency spatial vector tiles (MVT) for interactive mapping
- **Advanced Analytics**: Temporal growth analysis and categorical breakdowns
- **PostgreSQL Integration**: Robust database operations with async connection pooling
- **Automatic Data Population**: Smart database initialization with MaStR data processing
- **Dynamic Filtering**: Query parameter-based filtering for all endpoints
- **GeoJSON Output**: Standardized geospatial data format for mapping applications
- **Comprehensive Logging**: Configurable logging system with multiple verbosity levels
- **Docker Support**: Containerized deployment with docker-compose
- **MaStR Integration**: Direct integration with German energy market registry data

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   PostgreSQL    │    │   MaStR Data    │
│                 │    │   Database      │    │   (Bundesnetz-  │
│ • REST Endpoints│◄──►│ • Wind turbines │    │    agentur)     │
│ • Vector Tiles  │    │ • Solar panels  │    │                 │
│ • Analytics API │    │ • Other RE units│    │ • XML Downloads │
│ • GeoJSON API   │    │ • Spatial Index │    │ • Processing    │
│ • Health checks │    │ • Async Pool    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       ▲                       │
         └───────────────────────┼───────────────────────┘
                         Auto-population
                     (runs on first startup)
                              │
                              ▼
                    ┌─────────────────┐
                    │   Vector Tiles  │
                    │   (MVT Format)  │
                    │                 │
                    │ • High Performance│
                    │ • Spatial Index  │
                    │ • Dynamic Filter │
                    └─────────────────┘
```

## 📋 API Endpoints

### 🗺️ Vector Tile Service (High Performance)

**GET** `/api/tiles/{unit_type}/{z}/{x}/{y}`

Serves Mapbox Vector Tiles (MVT) optimized for interactive mapping applications.

**Parameters:**
- `unit_type`: Type of energy unit (`wind`, `solar`, `storage`, `biomass`, `hydro`, `combustion`, `nuclear`)
- `z`: Zoom level (0-19)
- `x`, `y`: Tile coordinates
- **Dynamic Filtering**: Any filter column can be passed as query parameters

**Example:**
```bash
# Get wind turbine tiles with filtering
curl "http://localhost:8000/api/tiles/wind/10/546/350?Hersteller=Enercon&WindAnLandOderAufSee=Land"

# Get solar tiles filtered by type
curl "http://localhost:8000/api/tiles/solar/12/2184/1400?ArtDerSolaranlage=Freiflächenanlage"
```

**Response:** Binary MVT data (`application/vnd.mapbox-vector-tile`)

**Performance Features:**
- Spatial index optimization (transforms tile envelope instead of geometries)
- Direct binary encoding without Python object conversion
- Async database operations for high throughput
- CORS enabled for cross-origin tile requests

### 📊 Advanced Analytics

**GET** `/api/stats/advanced/{unit_type}`

Provides comprehensive temporal and categorical analytics.

**Response:**
```json
{
  "temporal": [
    {"year": 2020, "count": 1250, "capacity": 3500.5},
    {"year": 2021, "count": 1420, "capacity": 4100.2},
    {"year": 2022, "count": 1680, "capacity": 4800.7}
  ],
  "status": [
    {"status": "In Betrieb", "count": 4200},
    {"status": "Außer Betrieb", "count": 150}
  ],
  "categories": {
    "column": "Hersteller",
    "data": [
      {"category": "Enercon", "capacity": 1200.5},
      {"category": "Vestas", "capacity": 950.2},
      {"category": "GE Renewable Energy", "capacity": 750.8}
    ]
  }
}
```

### 🔍 Metadata API

**GET** `/api/metadata/{unit_type}`

Returns unique values for filterable columns to populate UI controls.

**Response:**
```json
{
  "Bundesland": ["Bayern", "Niedersachsen", "Schleswig-Holstein"],
  "EinheitBetriebsstatus": ["In Betrieb", "Außer Betrieb", "Geplant"],
  "Hersteller": ["Enercon", "Vestas", "GE Renewable Energy", "Nordex"],
  "WindAnLandOderAufSee": ["Land", "Auf See"]
}
```

### 📈 Basic Statistics

**GET** `/api/stats?unit_type={unit_type}`

Returns basic statistics by Bundesland.

**Response:**
```json
[
  {"Bundesland": "Niedersachsen", "count": 1250, "total_capacity": 3500.5},
  {"Bundesland": "Bayern", "count": 980, "total_capacity": 2800.2},
  {"Bundesland": "Schleswig-Holstein", "count": 850, "total_capacity": 2400.7}
]
```

### 🗺️ Legacy GeoJSON API

**GET** `/api/units`

Returns geojson features for energy units with optional filtering.

**Parameters:**
- `unit_type` (required): Type of energy unit
- `min_lat`, `min_lon`, `max_lat`, `max_lon` (optional): Bounding box coordinates
- `limit` (optional): Maximum number of results (default: 5000)

**Example:**
```bash
curl "http://localhost:8000/api/units?unit_type=wind&limit=100"
```

### 📋 Table Information

**GET** `/api/tables`

Returns a list of all available database tables.

**Response:**
```json
{
  "tables": [
    {"table_name": "wind_extended"},
    {"table_name": "solar_extended"},
    {"table_name": "storage_extended"}
  ]
}
```

### 🏛️ Bundesländer

**GET** `/api/bundeslaender`

Returns all available Bundesländer.

**Response:**
```json
["Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", ...]
```

## 🛠️ Technical Implementation

### Vector Tile Pipeline Optimization

The most critical endpoint is `/api/tiles/{unit_type}/{z}/{x}/{y}`. 

**Spatial Query Optimization:**
When a tile is requested, we perform a spatial intersection. However, performing `ST_Transform` on millions of points is slow. 

**Optimization:** We transform the **Tile Envelope** (the box requested) from Web Mercator (3857) back to the database SRID (4326). This allows the query to utilize the **GIST Spatial Index** on the `geom` column.

```sql
WHERE geom && ST_Transform(ST_TileEnvelope($1, $2, $3), 4326)
```

**Direct Binary Encoding:**
Instead of converting database rows to Python objects and then to JSON, we use PostGIS's native binary encoding:
- `ST_AsMVTGeom`: Clips and scales geometries to the tile coordinate system.
- `ST_AsMVT`: Aggregates rows into a single binary Mapbox Vector Tile (MVT) blob.
This blob is sent directly to the client as `application/vnd.mapbox-vector-tile`.

### Analytics Engine

The `/api/stats/advanced/{unit_type}` endpoint provides a three-dimensional view of the data:
1. **Temporal:** Groups by `EXTRACT(YEAR FROM Inbetriebnahmedatum)` to show growth.
2. **Categorical:** Dynamic grouping based on unit type (e.g., `Hersteller` for Wind).
3. **Status:** Real-time breakdown of operational status.

### Database Architecture

**AsyncPG Connection Pooling:**
- Managed via `AsyncPG` to handle high-frequency requests without exhausting database connections
- Configurable pool size (min: 5, max: 10 connections)
- Proper connection lifecycle management with FastAPI lifespan events

**Filterable Columns by Unit Type:**
- **Common:** `Bundesland`, `EinheitBetriebsstatus`
- **Solar:** `ArtDerSolaranlage`, `Lage`
- **Wind:** `Hersteller`, `WindAnLandOderAufSee`
- **Biomass:** `Biomasseart`, `Hauptbrennstoff`
- **Storage:** `Batterietechnologie`, `Einsatzort`
- **Hydro:** `ArtDerWasserkraftanlage`
- **Combustion:** `Hauptbrennstoff`, `Technologie`
- **Nuclear:** `Technologie`

## 🚀 Quick Start with Docker

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

## 🔧 Local Development

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

## ⚙️ Configuration

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

### CORS Configuration

The backend is configured to allow cross-origin requests for seamless integration with frontend applications:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📊 Project Structure

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

## 🎯 Why FastAPI + AsyncPG?

- **FastAPI:** Handles tile requests in a non-blocking event loop. When one request is waiting for the database, another can be served.
- **AsyncPG:** Bypasses the overhead of an ORM (like SQLAlchemy) for maximum throughput.
- **Vector Tiles:** Serve thousands of points efficiently with spatial indexing and binary encoding.
- **Analytics:** Real-time aggregation and temporal analysis for data insights.

## 📈 Performance Considerations

### Vector Tile Performance
- **Spatial Indexes:** GIST indexes on geometry columns for fast spatial queries
- **Binary Encoding:** Direct MVT generation without Python object conversion
- **Async Operations:** Non-blocking database operations for high concurrency
- **Tile Caching:** Consider implementing Redis or CDN caching for popular tiles

### Database Optimization
- **Connection Pooling:** Configurable pool size to balance memory usage and performance
- **Index Strategy:** Spatial indexes on geometry columns, B-tree indexes on filter columns
- **Query Optimization:** Transform tile envelope instead of individual geometries

### Memory Management
- **Streaming:** Large dataset processing with memory-efficient streaming
- **Batch Operations:** Bulk inserts and updates for data population
- **Resource Cleanup:** Proper connection lifecycle management

## 🔍 Monitoring and Logs

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

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Ensure PostgreSQL is running and accessible
   - Check environment variables in `.env`
   - Verify database credentials

2. **No Data Returned**
   - Check if database population completed successfully
   - Verify table names and unit types
   - Check API logs for errors

3. **Slow Vector Tile Responses**
   - Ensure spatial indexes are created
   - Check PostgreSQL performance settings
   - Consider reducing tile complexity or implementing caching

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

-- Check spatial index usage
EXPLAIN ANALYZE SELECT COUNT(*) FROM wind_extended 
WHERE geom && ST_Transform(ST_TileEnvelope(10, 546, 350), 4326);
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 Data Sources

- **MaStR Database**: Official German energy market registry maintained by Bundesnetzagentur
- **Data Updates**: MaStR data is updated regularly. The orchestrator downloads the latest available dataset
- **Coverage**: Germany-wide renewable energy infrastructure data
- **License**: Data is publicly available under German open data policies

## 📞 Support

For issues and questions:
1. Check the logs for error messages
2. Verify your environment configuration
3. Review the API documentation at `/docs`
4. Check existing issues in the project repository