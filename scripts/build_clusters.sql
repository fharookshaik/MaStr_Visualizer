-- MIT License
-- Copyright (c) 2026 MaStR Visualizer contributors
-- Small spatial cells are grouped by all filter dimensions before MapLibre clustering.

COPY (
    SELECT
        FLOOR(lat * 4) / 4.0 + 0.125 AS grid_lat,
        FLOOR(lon * 4) / 4.0 + 0.125 AS grid_lon,
        tech_type,
        status,
        state,
        COUNT(*) AS unit_count,
        COALESCE(SUM(capacity_mw), 0)::DOUBLE AS capacity_mw
    FROM read_parquet('public/data/units.parquet')
    WHERE lat IS NOT NULL AND lon IS NOT NULL
    GROUP BY grid_lat, grid_lon, tech_type, status, state
) TO 'public/data/map-clusters.csv' (HEADER, DELIMITER ',');
