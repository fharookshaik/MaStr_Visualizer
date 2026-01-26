# Data Processing Guide

This document provides comprehensive information about the MaStr data source, processing pipeline, and data management in the MaStr Visualizer project.

## Data Source Overview

### Official MaStR Registry

**Source**: [Marktstammdatenregister (MaStR)](https://www.marktstammdatenregister.de/)

**Authority**: German Federal Network Agency (Bundesnetzagentur)

**Coverage**: Complete German energy market infrastructure data

**Update Frequency**: Regular updates from official source

**License**: German open data policies - free for public use

### Data Content

The MaStR database contains comprehensive information about:

- **Wind Energy**: Onshore and offshore wind turbines
- **Solar Energy**: Rooftop and ground-mounted solar installations
- **Energy Storage**: Battery and other storage systems
- **Biomass**: Biogas and biomass power plants
- **Hydro**: Hydroelectric power plants
- **Combustion**: Fossil fuel power plants
- **Nuclear**: Nuclear power plants

### Data Format

- **Primary Format**: XML downloads from official source
- **Processed Format**: Structured PostgreSQL tables with spatial data
- **Spatial Reference**: WGS84 (EPSG:4326)
- **Coordinate System**: Geographic coordinates (latitude/longitude)

## Processing Library: mastr_lite

### Overview

The `mastr_lite` library is a **customized version** of the [open-mastr](https://github.com/OpenEnergyPlatform/open-mastr) Python package, specifically adapted for this visualization project.

### Key Differences from open-mastr

1. **Streamlined Processing**: Optimized for visualization use cases
2. **Spatial Data Focus**: Enhanced spatial data handling and indexing
3. **Performance Optimization**: Bulk operations and efficient data loading
4. **Custom Schema**: Tailored database schema for mapping and analytics

### Core Components

#### 1. Data Download (`MaStrDownloader`)

**Location**: `backend/mastr_lite/utils/download_mastr.py`

**Purpose**: Downloads XML data from official MaStR source

**Features**:
- **Progress Tracking**: Real-time download progress
- **Error Handling**: Robust error handling and retry logic
- **File Management**: Automatic file organization and cleanup
- **Checksum Verification**: Data integrity verification

**Usage**:
```python
from mastr_lite.utils.download_mastr import MaStrDownloader

# Download latest data
downloader = MaStrDownloader(output_dir="/path/to/downloads")
zip_file = downloader.download_latest()
```

#### 2. Data Processing (`MaStrProcessor`)

**Location**: `backend/mastr_lite/main.py`

**Purpose**: Processes XML data into structured format

**Features**:
- **XML Parsing**: Efficient XML parsing with lxml
- **Data Validation**: Comprehensive data validation
- **Cleansing**: Data quality improvement and standardization
- **Bulk Loading**: High-performance database loading

**Processing Pipeline**:
1. **Extract**: Parse XML and extract relevant data
2. **Transform**: Cleanse, validate, and transform data
3. **Load**: Bulk insert into PostgreSQL with spatial data

**Usage**:
```python
from mastr_lite import MaStrProcessor
from mastr_lite.utils import DBConfig

# Configure database
db_config = DBConfig(
    DB_HOST="localhost",
    DB_PORT=5432,
    DB_NAME="mastr_db",
    DB_USER="postgres",
    DB_PASSWORD="password",
    DB_SCHEMA="public"
)

# Process data
processor = MaStrProcessor(db_config=db_config)
processor.process_zip(
    zip_file_path="/path/to/mastr_data.zip",
    bulk_cleansing=True,
    data=['wind', 'solar']  # Process specific data types
)
```

#### 3. Database Integration (`DBHelper`)

**Location**: `backend/mastr_lite/utils/db.py`

**Purpose**: Manages database connections and operations

**Features**:
- **Connection Management**: Efficient database connection pooling
- **PostGIS Setup**: Automatic PostGIS extension and spatial setup
- **Index Creation**: Automatic spatial and performance index creation
- **Bulk Operations**: Optimized bulk insert and update operations

**Usage**:
```python
from mastr_lite.utils.db import DBHelper

# Initialize database helper
db_helper = DBHelper(db_config=db_config)

# Enable PostGIS
postgis_enabled = db_helper.enable_postgis()

# Create spatial indexes
if postgis_enabled:
    db_helper.create_geometry_indexes(srid=4326)
```

## Data Processing Pipeline

### 1. Initial Setup

```python
from mastr_lite import DBConfig, MaStrDownloader, MaStrProcessor, DBHelper

# Configure database connection
db_config = DBConfig(
    DB_HOST="db",
    DB_PORT=5432,
    DB_NAME="mastr_db",
    DB_USER="postgres",
    DB_PASSWORD="1234",
    DB_SCHEMA="public"
)
```

### 2. Data Download

```python
# Download latest MaStR data
downloader = MaStrDownloader(output_dir="./downloads")
zip_file = downloader.download_latest()
```

### 3. Data Processing

```python
# Process the downloaded data
processor = MaStrProcessor(db_config=db_config)
processor.process_zip(
    zip_file_path=str(zip_file),
    bulk_cleansing=True,
    data=['wind', 'solar', 'storage']  # Specify data types to process
)
```

### 4. Database Setup

```python
# Set up spatial database features
db_helper = DBHelper(db_config=db_config)
postgis_enabled = db_helper.enable_postgis()

if postgis_enabled:
    db_helper.create_geometry_indexes(srid=4326)
else:
    logger.warning("Spatial features disabled (PostGIS not available).")
```

## Database Schema

### Table Structure

Each energy unit type has its own extended table:

- `wind_extended` - Wind energy installations
- `solar_extended` - Solar energy installations
- `storage_extended` - Energy storage systems
- `biomass_extended` - Biomass power plants
- `hydro_extended` - Hydroelectric power plants
- `combustion_extended` - Combustion power plants
- `nuclear_extended` - Nuclear power plants

### Key Fields

#### Common Fields (All Tables)
- `EinheitMastrNummer` - Unique identifier
- `NameStromerzeugungseinheit` - Unit name
- `Bruttoleistung` - Capacity in kW
- `Bundesland` - Federal state
- `EinheitBetriebsstatus` - Operational status
- `geom` - Spatial geometry (Point)

#### Type-Specific Fields

**Wind Energy**:
- `Hersteller` - Manufacturer
- `WindAnLandOderAufSee` - Location type (Land/Sea)
- `Nabenhoehe` - Hub height
- `Rotordurchmesser` - Rotor diameter

**Solar Energy**:
- `ArtDerSolaranlage` - Solar installation type
- `Lage` - Location type
- `Modulflaeche` - Module area
- `Wechselrichteranzahl` - Inverter count

**Storage**:
- `Batterietechnologie` - Battery technology
- `Einsatzort` - Deployment location
- `Nennleistung` - Rated power
- `Nennenergie` - Rated energy

### Spatial Data

All tables include spatial geometry columns:

- **SRID**: 4326 (WGS84)
- **Geometry Type**: Point
- **Coordinate Order**: Longitude, Latitude
- **Index**: GIST spatial index for performance

### Index Strategy

#### Spatial Indexes
```sql
-- Automatic spatial index creation
CREATE INDEX idx_wind_extended_geom ON wind_extended USING GIST (geom);
```

#### Performance Indexes
```sql
-- Common filter columns
CREATE INDEX idx_wind_extended_bundesland ON wind_extended ("Bundesland");
CREATE INDEX idx_wind_extended_status ON wind_extended ("EinheitBetriebsstatus");
CREATE INDEX idx_wind_extended_hersteller ON wind_extended ("Hersteller");
```

## Data Quality and Validation

### Validation Rules

1. **Coordinate Validation**: Ensure valid latitude/longitude ranges
2. **Capacity Validation**: Non-negative capacity values
3. **Status Validation**: Valid operational status codes
4. **Identifier Uniqueness**: Unique MaStR numbers
5. **Spatial Validity**: Valid geometry objects

### Data Cleansing

#### Bulk Cleansing Operations
- **Null Value Handling**: Replace nulls with appropriate defaults
- **Duplicate Removal**: Remove duplicate entries
- **Format Standardization**: Standardize text formats
- **Range Validation**: Validate numeric ranges

#### Quality Assurance
- **Row Count Verification**: Compare with expected counts
- **Spatial Coverage**: Verify geographic coverage
- **Data Completeness**: Check for missing critical fields
- **Consistency Checks**: Cross-table consistency validation

## Performance Optimization

### Bulk Loading

#### Batch Processing
```python
# Process data in batches for memory efficiency
batch_size = 10000
for batch in data_batches:
    db_helper.bulk_insert(table_name, batch)
```

#### Memory Management
- **Streaming Processing**: Process data in chunks
- **Temporary Storage**: Use temporary files for large datasets
- **Resource Cleanup**: Proper cleanup of temporary resources

### Query Optimization

#### Spatial Query Patterns
```sql
-- Efficient spatial queries using tile envelope
SELECT * FROM wind_extended 
WHERE geom && ST_Transform(ST_TileEnvelope(10, 546, 350), 4326)
```

#### Index Usage
- **GIST Indexes**: For spatial queries
- **B-tree Indexes**: For categorical filtering
- **Composite Indexes**: For multi-column queries

## Data Updates and Maintenance

### Regular Updates

#### Automated Update Process
```python
def update_mastr_data():
    """Automated MaStR data update process."""
    # 1. Download latest data
    zip_file = MaStrDownloader().download_latest()
    
    # 2. Process new data
    processor = MaStrProcessor(db_config)
    processor.process_zip(zip_file_path=str(zip_file))
    
    # 3. Update indexes
    db_helper = DBHelper(db_config)
    db_helper.create_geometry_indexes(srid=4326)
    
    # 4. Update statistics
    db_helper.update_table_statistics()
```

#### Update Frequency
- **Recommended**: Monthly updates
- **Minimum**: Quarterly updates
- **Real-time**: Not supported (batch processing only)

### Data Archiving

#### Historical Data Management
- **Versioning**: Keep previous versions for comparison
- **Archiving**: Archive old data to separate storage
- **Cleanup**: Remove obsolete temporary files

#### Backup Strategy
```bash
# Database backup
pg_dump -U postgres mastr_db > backup_$(date +%Y%m%d).sql

# Data file backup
tar -czf data_backup_$(date +%Y%m%d).tar.gz /path/to/data/files
```

## Troubleshooting

### Common Issues

#### Download Failures
```bash
# Check internet connection
ping www.marktstammdatenregister.de

# Verify download directory permissions
ls -la /path/to/downloads

# Check available disk space
df -h
```

#### Processing Errors
```bash
# Check XML file integrity
file /path/to/mastr_data.zip

# Verify database connection
psql -U postgres -d mastr_db -c "SELECT version();"

# Check processing logs
tail -f /path/to/processing.log
```

#### Performance Issues
```bash
# Monitor database performance
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC;

# Check index usage
SELECT indexname, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE tablename LIKE '%extended%';
```

### Data Quality Issues

#### Missing Data
- **Coordinate Issues**: Check for null or invalid coordinates
- **Capacity Issues**: Verify capacity values are reasonable
- **Status Issues**: Ensure operational status is valid

#### Inconsistencies
- **Duplicate Entries**: Check for duplicate MaStR numbers
- **Spatial Issues**: Verify geometry validity
- **Format Issues**: Standardize text formats

## Integration with External Systems

### Data Export

#### CSV Export
```python
import pandas as pd

# Export to CSV
query = "SELECT * FROM wind_extended LIMIT 1000"
df = pd.read_sql(query, connection)
df.to_csv('wind_data.csv', index=False)
```

#### GeoJSON Export
```python
# Export spatial data as GeoJSON
query = """
SELECT jsonb_build_object(
    'type', 'FeatureCollection',
    'features', jsonb_agg(features.feature)
) FROM (
    SELECT jsonb_build_object(
        'type', 'Feature',
        'geometry', ST_AsGeoJSON(geom)::jsonb,
        'properties', to_jsonb(t) - 'geom'
    ) AS feature
    FROM wind_extended t
) features;
"""
```

### API Integration

#### REST API Endpoints
- **Vector Tiles**: `/api/tiles/{unit_type}/{z}/{x}/{y}`
- **Analytics**: `/api/stats/advanced/{unit_type}`
- **Metadata**: `/api/metadata/{unit_type}`

#### Data Access Patterns
- **Real-time Queries**: For interactive applications
- **Batch Processing**: For data analysis
- **Spatial Analysis**: For GIS applications

This data processing guide provides comprehensive information for understanding, managing, and maintaining the MaStr data in the visualization system.