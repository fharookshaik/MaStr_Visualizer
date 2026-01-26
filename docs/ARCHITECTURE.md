# Architecture Guide

This document provides a comprehensive overview of the MaStr Visualizer's technical architecture, design decisions, and system components.

## System Overview

The MaStr Visualizer follows a **three-tier architecture** with clear separation of concerns:

1. **Presentation Layer**: Streamlit frontend with interactive dashboards
2. **Application Layer**: FastAPI backend with RESTful services
3. **Data Layer**: PostgreSQL with PostGIS for spatial data management

## Component Architecture

### Frontend (Streamlit + PyDeck)

**Location**: `frontend/`

**Purpose**: User interface and interactive visualization layer

**Key Technologies**:
- **Streamlit**: Python web framework for data applications
- **PyDeck**: WebGL-based mapping library for high-performance spatial visualization
- **Plotly**: Interactive charting and analytics visualization
- **Folium**: Alternative mapping library for compatibility

**Components**:
- **Dashboard**: Main application interface with tabs for Map Explorer and Analytics
- **Map Explorer**: Interactive map with vector tile rendering
- **Analytics Tab**: Charts and statistics for data insights
- **Filter Controls**: Dynamic UI elements for data filtering

**Performance Features**:
- **WebGL Rendering**: GPU-accelerated mapping for large datasets
- **Vector Tiles**: Efficient spatial data transmission and rendering
- **Caching**: Streamlit's built-in caching for data and computations
- **Responsive Design**: Works across desktop and mobile devices

### Backend (FastAPI + AsyncPG)

**Location**: `backend/`

**Purpose**: API services, data processing, and business logic

**Key Technologies**:
- **FastAPI**: High-performance async web framework
- **AsyncPG**: Async PostgreSQL driver for high concurrency
- **SQLAlchemy**: ORM for database operations
- **Pydantic**: Data validation and serialization

**Core Services**:

#### 1. Vector Tile Service
```python
@app.get("/api/tiles/{unit_type}/{z}/{x}/{y}")
async def get_tiles(unit_type: str, z: int, x: int, y: int, request: Request):
    # High-performance spatial queries with PostGIS
    # Returns binary MVT data for efficient mapping
```

**Optimization Features**:
- **Spatial Indexing**: Uses GIST indexes on geometry columns
- **Coordinate Transformation**: Transforms tile envelope instead of individual geometries
- **Binary Encoding**: Direct MVT generation without Python object conversion
- **Async Operations**: Non-blocking database queries for high throughput

#### 2. Analytics API
```python
@app.get("/api/stats/advanced/{unit_type}")
async def get_advanced_stats(unit_type: str):
    # Temporal growth analysis and categorical breakdowns
    # Real-time aggregation and statistical analysis
```

**Analytics Capabilities**:
- **Temporal Analysis**: Growth trends by year/month
- **Categorical Breakdowns**: Analysis by manufacturer, technology, status
- **Spatial Aggregation**: Regional capacity and count statistics
- **Real-time Processing**: On-demand data aggregation

#### 3. Metadata Service
```python
@app.get("/api/metadata/{unit_type}")
async def get_metadata(unit_type: str):
    # Returns filterable column values for dynamic UI
```

**Dynamic Filtering**:
- **Column Discovery**: Automatically detects filterable columns per unit type
- **Value Extraction**: Unique values for dropdown and multiselect controls
- **Type-specific Filters**: Different filters for wind, solar, storage, etc.

### Data Layer (PostgreSQL + PostGIS)

**Purpose**: Spatial data storage and management

**Key Features**:
- **PostGIS Extension**: Spatial database capabilities
- **GIST Indexes**: Optimized spatial queries
- **Async Connection Pooling**: Efficient database resource management
- **Bulk Operations**: High-performance data loading

**Database Schema**:
- **Extended Tables**: Each unit type has an extended table with spatial data
- **Geometry Columns**: Spatial coordinates in WGS84 (EPSG:4326)
- **Index Strategy**: Spatial indexes on geometry, B-tree on filter columns
- **Data Types**: Proper types for capacity (numeric), dates, and categorical data

### Data Processing (mastr_lite)

**Location**: `backend/mastr_lite/`

**Purpose**: Customized open-mastr integration for data processing

**Key Components**:

#### 1. Data Download
```python
class MaStrDownloader:
    # Downloads XML data from official MaStR source
    # Handles large file downloads with progress tracking
```

#### 2. Data Processing
```python
class MaStrProcessor:
    # Processes XML data into structured format
    # Handles data cleansing and validation
    # Performs bulk database operations
```

#### 3. Database Integration
```python
class DBHelper:
    # Manages database connections and operations
    # Handles PostGIS setup and spatial indexes
    # Provides bulk loading capabilities
```

**Processing Pipeline**:
1. **Download**: Fetch latest XML data from MaStR
2. **Extract**: Parse XML and extract relevant data
3. **Transform**: Cleanse, validate, and transform data
4. **Load**: Bulk insert into PostgreSQL with spatial data
5. **Index**: Create spatial and performance indexes

## Data Flow Architecture

### 1. Initial Data Population

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MaStR Source  │───▶│   mastr_lite    │───▶│   PostgreSQL    │
│   (XML Data)    │    │   (Processing)  │    │   (Storage)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                         Auto-population
                     (runs on first startup)
```

### 2. User Request Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Request  │───▶│   FastAPI       │───▶│   PostgreSQL    │
│   (Frontend)    │    │   (Backend)     │    │   (Query)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                         Vector Tiles
                     (Spatial Queries)
```

### 3. Analytics Request Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Analytics     │───▶│   FastAPI       │───▶│   PostgreSQL    │
│   Request       │    │   (Aggregation) │    │   (Analytics)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                         Aggregated Data
                     (Real-time Processing)
```

## Performance Optimization Strategies

### 1. Spatial Query Optimization

**Problem**: Large datasets with millions of spatial points require efficient querying.

**Solution**:
- **GIST Spatial Indexes**: Fast spatial intersection queries
- **Tile Envelope Transformation**: Transform tile bounds instead of individual geometries
- **Binary MVT Encoding**: Direct binary tile generation

**Query Pattern**:
```sql
-- Efficient spatial query using tile envelope
SELECT ST_AsMVTGeom(
    ST_Transform(geom, 3857), 
    ST_TileEnvelope($1, $2, $3), 
    4096, 256, true
) FROM table_name 
WHERE geom && ST_Transform(ST_TileEnvelope($1, $2, $3), 4326)
```

### 2. Async Database Operations

**Problem**: Synchronous database operations block the event loop.

**Solution**:
- **AsyncPG Connection Pool**: Non-blocking database connections
- **Async Context Managers**: Proper resource management
- **Concurrent Requests**: Handle multiple requests simultaneously

**Implementation**:
```python
# Async database connection
async with db.pool.acquire() as conn:
    result = await conn.fetch(query, *params)
```

### 3. Frontend Performance

**Problem**: Large datasets cause frontend rendering issues.

**Solution**:
- **Vector Tiles**: Efficient spatial data transmission
- **WebGL Rendering**: GPU-accelerated mapping
- **Caching**: Streamlit's built-in caching for expensive operations
- **Lazy Loading**: Load data on demand

### 4. Memory Management

**Problem**: Large XML processing and data loading consume excessive memory.

**Solution**:
- **Streaming Processing**: Process data in chunks
- **Bulk Operations**: Minimize database round trips
- **Resource Cleanup**: Proper cleanup of temporary files and connections

## Technology Choices Rationale

### FastAPI over Flask/Django
- **Performance**: Async support and automatic OpenAPI generation
- **Type Safety**: Pydantic models for data validation
- **Modern**: Built-in support for modern web standards

### Streamlit over Traditional Frontend
- **Rapid Development**: Python-based frontend development
- **Data Focus**: Built-in support for data visualization
- **Integration**: Seamless integration with Python data stack

### PostgreSQL + PostGIS over Other Databases
- **Spatial Capabilities**: Industry-standard spatial database
- **Performance**: Excellent spatial query performance
- **Reliability**: Mature, stable, and well-supported

### PyDeck over Folium/Leaflet
- **Performance**: WebGL-based rendering for large datasets
- **3D Capabilities**: Support for 3D visualization
- **Integration**: Native integration with Streamlit

## Scalability Considerations

### Horizontal Scaling
- **Stateless Backend**: FastAPI services can be load-balanced
- **Database Read Replicas**: For read-heavy analytics workloads
- **CDN Integration**: For vector tile caching

### Vertical Scaling
- **Memory Optimization**: Efficient data structures and processing
- **CPU Optimization**: Async operations and parallel processing
- **Storage Optimization**: Proper indexing and data organization

### Future Enhancements
- **Redis Caching**: For frequently accessed data and tiles
- **Message Queues**: For background data processing
- **Microservices**: Breaking down into smaller, focused services

## Security Considerations

### Data Security
- **Environment Variables**: Database credentials stored securely
- **Network Isolation**: Docker network isolation between services
- **Input Validation**: Pydantic models for API input validation

### Access Control
- **CORS Configuration**: Controlled cross-origin resource sharing
- **API Documentation**: Public API docs with proper authentication
- **Database Permissions**: Limited database user permissions

This architecture provides a solid foundation for a high-performance, scalable energy data visualization platform while maintaining simplicity and ease of development.