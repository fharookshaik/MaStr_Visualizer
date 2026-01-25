from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List
from utils import DBConfigenv, Database

from logger import logger


# GLOBALS
TABLE_MAPPING = {
    "solar": "solar_extended",
    "wind": "wind_extended",
    "storage": "storage_extended",
    "biomass": "biomass_extended",
    "hydro": "hydro_extended",
    "combustion": "combustion_extended",
    "nuclear": "nuclear_extended",
}

# Columns are filterable per unit type
FILTER_COLUMNS = {
    "common": ["Bundesland", "EinheitBetriebsstatus"],
    "solar": ["ArtDerSolaranlage", "Lage"],
    "wind": ["Hersteller", "WindAnLandOderAufSee"],
    "biomass": ["Biomasseart", "Hauptbrennstoff"],
    "storage": ["Batterietechnologie", "Einsatzort"],
    "hydro": ["ArtDerWasserkraftanlage"],
    "combustion": ["Hauptbrennstoff", "Technologie"],
    "nuclear": ["Technologie"]
}


# Create database instance
config = DBConfigenv()
db = Database(config.get_dsn())

# Dependency for FastAPI routes
async def get_db():
    """
    Dependency to get a database connection from the pool.

    Use in routes: async def route(conn=Depends(get_db)):
    """
    if db.pool is None:
        raise HTTPException(status_code=500, detail="Database not connected.")
    async with db.pool.acquire() as conn:
        yield conn


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()
    yield
    # Shutdown
    await db.disconnect()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/metadata/{unit_type}")
async def get_metadata(unit_type: str, conn=Depends(get_db)):
    """Returns unique values for filterable columns based on unit type."""
    table_name = TABLE_MAPPING.get(unit_type)
    if not table_name:
        logger.error(f"No such table {table_name}")
        raise HTTPException(status_code=400, detail="Invalid unit_type")
    
    cols = FILTER_COLUMNS.get("common", []) + FILTER_COLUMNS.get(unit_type, [])
    metadata = {}
    
    try:
        for col in cols:
            query = f'SELECT DISTINCT "{col}" FROM "{table_name}" WHERE "{col}" IS NOT NULL ORDER BY 1'
            records = await conn.fetch(query)
            metadata[col] = [r[col] for r in records]
        return metadata
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tiles/{unit_type}/{z}/{x}/{y}")
async def get_tiles(
    unit_type: str, z: int, x: int, y: int, 
    request: Request,
    conn=Depends(get_db)
):
    table_name = TABLE_MAPPING.get(unit_type)
    if not table_name:
        return Response(content=b"", media_type="application/vnd.mapbox-vector-tile")

    # Dynamic Filtering from query params
    params = [z, x, y]
    where_clauses = ['geom && ST_Transform(ST_TileEnvelope($1, $2, $3), 4326)']
    
    # Extract all filters from query params that match our filterable columns
    allowed_cols = FILTER_COLUMNS["common"] + FILTER_COLUMNS.get(unit_type, [])
    for key, value in request.query_params.items():
        if key in allowed_cols and value:
            vals = value.split(',')
            placeholders = [f'${len(params) + i + 1}' for i in range(len(vals))]
            where_clauses.append(f'"{key}" IN ({", ".join(placeholders)})')
            params.extend(vals)

    where_sql = " AND ".join(where_clauses)
    query = f"""
        WITH mvtgeom AS (
            SELECT "EinheitMastrNummer", "NameStromerzeugungseinheit" as "Name",
                   "Bruttoleistung", "Bundesland", "EinheitBetriebsstatus",
                ST_AsMVTGeom(ST_Transform(geom, 3857), ST_TileEnvelope($1, $2, $3), 4096, 256, true) AS geom
            FROM "{table_name}" WHERE {where_sql}
        )
        SELECT ST_AsMVT(mvtgeom.*, 'layer', 4096, 'geom') FROM mvtgeom;
    """
    try:
        result = await conn.fetchval(query, *params)
        return Response(content=result if result else b"", media_type="application/vnd.mapbox-vector-tile")
    except Exception as e:
        logger.error(f"Error generating tiles: {e}")
        return Response(content=b"", media_type="application/vnd.mapbox-vector-tile")

@app.get("/api/stats/advanced/{unit_type}")
async def get_advanced_stats(unit_type: str, conn=Depends(get_db)):
    """Returns temporal growth and categorical breakdown stats."""
    table_name = TABLE_MAPPING.get(unit_type)
    if not table_name:
        raise HTTPException(status_code=400, detail="Invalid unit_type")

    try:
        # Temporal Stats (Growth by Year)
        query_temporal = f"""
            SELECT EXTRACT(YEAR FROM "Inbetriebnahmedatum")::int as year,
                   COUNT(*) as count, SUM("Bruttoleistung") as capacity
            FROM "{table_name}"
            WHERE "Inbetriebnahmedatum" IS NOT NULL
            GROUP BY year ORDER BY year
        """
        
        # Status Breakdown
        query_status = f"""
            SELECT "EinheitBetriebsstatus" as status, COUNT(*) as count
            FROM "{table_name}" GROUP BY status
        """

        # Main Category Breakdown (Table specific)
        cat_col = FILTER_COLUMNS.get(unit_type, ["Technologie"])[0]
        query_cat = f"""
            SELECT "{cat_col}" as category, SUM("Bruttoleistung") as capacity
            FROM "{table_name}" WHERE "{cat_col}" IS NOT NULL
            GROUP BY category ORDER BY capacity DESC LIMIT 10
        """

        temporal = await conn.fetch(query_temporal)
        status = await conn.fetch(query_status)
        categories = await conn.fetch(query_cat)

        return {
            "temporal": [dict(r) for r in temporal],
            "status": [dict(r) for r in status],
            "categories": {"column": cat_col, "data": [dict(r) for r in categories]}
        }
    except Exception as e:
        logger.error(f"Error fetching advanced temporal stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_basic_stats(unit_type: str, conn=Depends(get_db)):
    try:
        table_name = TABLE_MAPPING.get(unit_type)
        query = f'SELECT "Bundesland", COUNT(*) as count, SUM("Bruttoleistung") as total_capacity FROM "{table_name}" WHERE "Bundesland" IS NOT NULL GROUP BY "Bundesland" ORDER BY total_capacity DESC'
        records = await conn.fetch(query)
        return [dict(r) for r in records]
    except Exception as e:
        logger.error(f"Error fetching basic stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bundeslaender")
async def get_bundeslaender(conn=Depends(get_db)):
    try:
        records = await conn.fetch('SELECT DISTINCT "Bundesland" FROM solar_extended WHERE "Bundesland" IS NOT NULL ORDER BY 1')
        return [r["Bundesland"] for r in records]
    except Exception as e:
        logger.error(f"Error fetching Bundeslander: {e}")
        raise HTTPException(status_code=500, detail=str(e))        