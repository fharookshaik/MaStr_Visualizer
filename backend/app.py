from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from utils import DBConfigenv, Database
from logger import logger

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


def to_geojson_feature(unit, unit_type, lat_col='Breitengrad', lon_col='Laengengrad'):
    """Converts a database record to a GeoJSON feature."""
    if not unit or not unit.get(lat_col) or not unit.get(lon_col):
        return None
    
    # Convert all values to string to avoid JSON serialization errors
    properties = {str(k): str(v) for k, v in unit.items() if k not in [lat_col, lon_col]}
    properties['unit_type'] = unit_type
    
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [float(unit[lon_col]), float(unit[lat_col])]
        },
        "properties": properties
    }


@app.get("/api/tables", response_model=Dict[str, Any])
async def get_tables(conn=Depends(get_db)):
    try:
        query = '''
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        '''

        units = await conn.fetch(query)

        # Convert records to list of dicts for JSON serialization
        return {"tables": [dict(record) for record in units]}
    except Exception as e:
        logger.error(f"Error fetching tables: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

@app.get("/api/units", response_model=Dict[str, Any])
async def get_units(conn=Depends(get_db),
                    unit_type: str = Query(..., description="Type of unit to retrieve"),
    min_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    limit: Optional[int] = Query(5000, description="Maximum number of units")):
    table_mapping = {
        "solar": "solar_extended",
        "wind": "wind_extended",
        "storage": "storage_extended",
        "biomass": "biomass_extended",
        "hydro": "hydro_extended",
        "combustion": "combustion_extended",
        "nuclear": "nuclear_extended",
    }
    table_name = table_mapping.get(unit_type)
    if not table_name:
        raise HTTPException(status_code=400, detail="Invalid unit_type")

    try:
        query = f'''
            SELECT "EinheitMastrNummer", "Breitengrad", "Laengengrad",
                   "NameStromerzeugungseinheit" as "Name"
            FROM "{table_name}"
            WHERE "Laengengrad" IS NOT NULL AND "Breitengrad" IS NOT NULL
        '''
        params = []

        if all([min_lat, min_lon, max_lat, max_lon]):
            query += ' AND "Breitengrad" BETWEEN $1 AND $2 AND "Laengengrad" BETWEEN $3 AND $4'
            params = [min_lat, max_lat, min_lon, max_lon]

        # THIS IS THE KEY CHANGE: Random order for even distribution
        query += ' ORDER BY RANDOM()'

        if limit and limit > 0:
            query += f' LIMIT {limit}'

        units = await conn.fetch(query, *params)

        features = [to_geojson_feature(dict(unit), unit_type) for unit in units]
        feature_collection = {
            "type": "FeatureCollection",
            "features": list(filter(None, features))
        }
        return feature_collection
    except Exception as e:
        logger.error(f"Error fetching units: {e}")
        raise HTTPException(status_code=500, detail="Internal error")
