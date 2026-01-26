# API Documentation

This document provides comprehensive documentation for the MaStr Visualizer RESTful API endpoints, including request/response formats, parameters, and usage examples.

## Base URL

```
http://localhost:8000/api/
```

## Authentication

The API is currently public and does not require authentication. For production deployments, consider implementing API key authentication or OAuth2.

## Response Format

All API responses are in JSON format unless otherwise specified. Vector tile endpoints return binary data.

### Standard Response Structure

```json
{
  "success": true,
  "data": {...},
  "message": "Optional message"
}
```

### Error Response Structure

```json
{
  "detail": "Error description"
}
```

## Endpoints

### 1. Vector Tile Service

**GET** `/tiles/{unit_type}/{z}/{x}/{y}`

Serves high-performance Mapbox Vector Tiles (MVT) for interactive mapping applications.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `unit_type` | string | Yes | Type of energy unit (`wind`, `solar`, `storage`, `biomass`, `hydro`, `combustion`, `nuclear`) |
| `z` | integer | Yes | Zoom level (0-19) |
| `x` | integer | Yes | Tile X coordinate |
| `y` | integer | Yes | Tile Y coordinate |

#### Query Parameters (Filtering)

Any filterable column can be passed as query parameters for dynamic filtering:

| Column Type | Available Filters |
|-------------|------------------|
| **Common** | `Bundesland`, `EinheitBetriebsstatus` |
| **Wind** | `Hersteller`, `WindAnLandOderAufSee` |
| **Solar** | `ArtDerSolaranlage`, `Lage` |
| **Biomass** | `Biomasseart`, `Hauptbrennstoff` |
| **Storage** | `Batterietechnologie`, `Einsatzort` |
| **Hydro** | `ArtDerWasserkraftanlage` |
| **Combustion** | `Hauptbrennstoff`, `Technologie` |
| **Nuclear** | `Technologie` |

#### Examples

```bash
# Get wind turbine tiles with filtering
curl "http://localhost:8000/api/tiles/wind/10/546/350?Hersteller=Enercon&WindAnLandOderAufSee=Land"

# Get solar tiles filtered by type
curl "http://localhost:8000/api/tiles/solar/12/2184/1400?ArtDerSolaranlage=Freiflächenanlage"

# Multiple values for a single filter
curl "http://localhost:8000/api/tiles/wind/10/546/350?Hersteller=Enercon,Vestas"
```

#### Response

**Content-Type**: `application/vnd.mapbox-vector-tile`

Binary MVT data that can be consumed by mapping libraries like Mapbox GL JS, Leaflet with plugins, or PyDeck.

#### Performance Notes

- **Spatial Indexing**: Uses GIST indexes for fast spatial queries
- **Binary Encoding**: Direct MVT generation without Python object conversion
- **Async Operations**: Non-blocking database queries
- **Tile Caching**: Consider implementing Redis or CDN caching for popular tiles

### 2. Advanced Analytics

**GET** `/stats/advanced/{unit_type}`

Provides comprehensive temporal and categorical analytics for the specified unit type.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `unit_type` | string | Yes | Type of energy unit |

#### Response Format

```json
{
  "temporal": [
    {
      "year": 2020,
      "count": 1250,
      "capacity": 3500.5
    },
    {
      "year": 2021,
      "count": 1420,
      "capacity": 4100.2
    }
  ],
  "status": [
    {
      "status": "In Betrieb",
      "count": 4200
    },
    {
      "status": "Außer Betrieb",
      "count": 150
    }
  ],
  "categories": {
    "column": "Hersteller",
    "data": [
      {
        "category": "Enercon",
        "capacity": 1200.5
      },
      {
        "category": "Vestas",
        "capacity": 950.2
      }
    ]
  }
}
```

#### Field Descriptions

- **temporal**: Array of yearly statistics
  - `year`: Calendar year
  - `count`: Number of units installed
  - `capacity`: Total capacity in kW

- **status**: Operational status breakdown
  - `status`: Status description (e.g., "In Betrieb", "Außer Betrieb")
  - `count`: Number of units in this status

- **categories**: Top categories by capacity
  - `column`: The categorized column name
  - `data`: Array of category data with capacity totals

#### Example

```bash
curl "http://localhost:8000/api/stats/advanced/wind"
```

### 3. Metadata Service

**GET** `/metadata/{unit_type}`

Returns unique values for filterable columns to populate UI controls dynamically.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `unit_type` | string | Yes | Type of energy unit |

#### Response Format

```json
{
  "Bundesland": ["Bayern", "Niedersachsen", "Schleswig-Holstein"],
  "EinheitBetriebsstatus": ["In Betrieb", "Außer Betrieb", "Geplant"],
  "Hersteller": ["Enercon", "Vestas", "GE Renewable Energy", "Nordex"],
  "WindAnLandOderAufSee": ["Land", "Auf See"]
}
```

#### Example

```bash
curl "http://localhost:8000/api/metadata/wind"
```

### 4. Basic Statistics

**GET** `/stats`

Returns basic statistics aggregated by Bundesland.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `unit_type` | string | Yes | Type of energy unit |

#### Response Format

```json
[
  {
    "Bundesland": "Niedersachsen",
    "count": 1250,
    "total_capacity": 3500.5
  },
  {
    "Bundesland": "Bayern",
    "count": 980,
    "total_capacity": 2800.2
  }
]
```

#### Example

```bash
curl "http://localhost:8000/api/stats?unit_type=wind"
```

### 5. Legacy GeoJSON API

**GET** `/units`

Returns GeoJSON features for energy units with optional filtering.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `unit_type` | string | Yes | Type of energy unit |
| `min_lat` | float | No | Minimum latitude for bounding box |
| `min_lon` | float | No | Minimum longitude for bounding box |
| `max_lat` | float | No | Maximum latitude for bounding box |
| `max_lon` | float | No | Maximum longitude for bounding box |
| `limit` | integer | No | Maximum number of results (default: 5000) |

#### Response Format

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "EinheitMastrNummer": "123456789",
        "NameStromerzeugungseinheit": "Windpark Example",
        "Bruttoleistung": 3000.5,
        "Bundesland": "Niedersachsen",
        "EinheitBetriebsstatus": "In Betrieb"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [8.5, 53.1]
      }
    }
  ]
}
```

#### Example

```bash
curl "http://localhost:8000/api/units?unit_type=wind&limit=100"
```

### 6. Table Information

**GET** `/tables`

Returns a list of all available database tables.

#### Response Format

```json
{
  "tables": [
    {"table_name": "wind_extended"},
    {"table_name": "solar_extended"},
    {"table_name": "storage_extended"}
  ]
}
```

#### Example

```bash
curl "http://localhost:8000/api/tables"
```

### 7. Bundesländer

**GET** `/bundeslaender`

Returns all available Bundesländer.

#### Response Format

```json
[
  "Baden-Württemberg",
  "Bayern",
  "Berlin",
  "Brandenburg",
  "Bremen",
  "Hamburg",
  "Hessen",
  "Mecklenburg-Vorpommern",
  "Niedersachsen",
  "Nordrhein-Westfalen",
  "Rheinland-Pfalz",
  "Saarland",
  "Sachsen",
  "Sachsen-Anhalt",
  "Schleswig-Holstein",
  "Thüringen"
]
```

#### Example

```bash
curl "http://localhost:8000/api/bundeslaender"
```

## Error Handling

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| `200` | Success |
| `400` | Bad Request (invalid parameters) |
| `404` | Not Found (invalid unit type) |
| `500` | Internal Server Error |

### Common Error Responses

```json
{
  "detail": "Invalid unit_type. Must be one of: wind, solar, storage, biomass, hydro, combustion, nuclear"
}
```

```json
{
  "detail": "Database connection failed"
}
```

## Rate Limiting

Currently, no rate limiting is implemented. For production deployments, consider implementing:

- Request rate limiting per IP
- Concurrent request limits
- Caching for frequently accessed data

## CORS Configuration

The API is configured to allow cross-origin requests:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For production, restrict `allow_origins` to your frontend domains.

## Integration Examples

### JavaScript (Fetch API)

```javascript
// Get vector tiles
const tileUrl = "http://localhost:8000/api/tiles/wind/10/546/350";

// Get analytics
fetch("http://localhost:8000/api/stats/advanced/wind")
  .then(response => response.json())
  .then(data => console.log(data));

// Get metadata for filters
fetch("http://localhost:8000/api/metadata/wind")
  .then(response => response.json())
  .then(metadata => {
    // Populate UI controls
    console.log(metadata.Bundesland);
  });
```

### Python (Requests)

```python
import requests

# Get basic stats
response = requests.get("http://localhost:8000/api/stats", params={"unit_type": "wind"})
stats = response.json()

# Get metadata
response = requests.get("http://localhost:8000/api/metadata/wind")
metadata = response.json()

# Get vector tiles (binary)
response = requests.get("http://localhost:8000/api/tiles/wind/10/546/350")
tile_data = response.content
```

### Mapbox GL JS Integration

```javascript
map.addSource('wind-tiles', {
  type: 'vector',
  tiles: ['http://localhost:8000/api/tiles/wind/{z}/{x}/{y}?Hersteller=Enercon'],
  minzoom: 0,
  maxzoom: 19
});

map.addLayer({
  id: 'wind-points',
  type: 'circle',
  source: 'wind-tiles',
  'source-layer': 'layer',
  paint: {
    'circle-radius': 5,
    'circle-color': '#ff8c00'
  }
});
```

## API Versioning

Currently, the API is at version 1.0. Future versions will be implemented using URL prefixes (e.g., `/api/v2/`) to maintain backward compatibility.

## Monitoring and Logging

### Log Levels

- `DEBUG`: Detailed debugging information
- `INFO`: General application operation
- `WARNING`: Potential issues
- `ERROR`: Error conditions
- `CRITICAL`: Critical errors

### Health Checks

The application includes health check endpoints for monitoring:

- Database connectivity
- API responsiveness
- Service availability

## Performance Considerations

### Vector Tiles
- Use appropriate zoom levels for your use case
- Implement client-side caching
- Consider server-side caching for popular tiles

### Analytics
- Results are cached for 5 minutes
- Large temporal ranges may impact performance
- Consider pagination for large result sets

### Database Queries
- Spatial queries use GIST indexes
- Filtered queries are optimized
- Bulk operations are used for data loading

This API provides comprehensive access to German energy infrastructure data with high performance and scalability.