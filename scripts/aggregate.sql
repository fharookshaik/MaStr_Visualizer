-- MIT License
-- Copyright (c) 2026 MaStR Visualizer contributors

CREATE OR REPLACE TEMP VIEW current_units AS
SELECT *
FROM read_parquet('public/data/units.parquet');

COPY (
    WITH technology_status AS (
        SELECT
            tech_type,
            status,
            COUNT(*) AS unit_count,
            SUM(capacity_mw)::DOUBLE AS capacity_mw
        FROM current_units
        GROUP BY tech_type, status
    ),
    current_week AS (
        SELECT
            strftime(current_date, '%G-W%V') AS week,
            tech_type,
            status,
            COUNT(*) AS unit_count,
            SUM(capacity_mw)::DOUBLE AS capacity_mw
        FROM current_units
        GROUP BY tech_type, status
    ),
    previous_week AS (
        SELECT week, tech_type, status, unit_count, capacity_mw
        FROM read_json('history.json', format = 'array', columns = {week: 'VARCHAR', tech_type: 'VARCHAR', status: 'VARCHAR', unit_count: 'BIGINT', capacity_mw: 'DOUBLE'}, union_by_name = true, ignore_errors = true, maximum_object_size = 100000000)
        WHERE week = strftime(current_date - INTERVAL 7 DAY, '%G-W%V')
    ),
    weekly_delta AS (
        SELECT
            current_week.week,
            current_week.tech_type,
            current_week.status,
            current_week.unit_count,
            current_week.unit_count - previous_week.unit_count AS delta_units,
            current_week.capacity_mw,
            current_week.capacity_mw - previous_week.capacity_mw AS delta_mw
        FROM current_week
        INNER JOIN previous_week USING (tech_type, status)
    ),
    municipality_technology AS (
        SELECT
            municipality_key,
            tech_type,
            COUNT(*) AS unit_count,
            SUM(capacity_mw)::DOUBLE AS capacity_mw
        FROM current_units
        WHERE municipality_key IS NOT NULL AND municipality_name IS NOT NULL
        GROUP BY municipality_key, tech_type
    ),
    municipality_tech_mix AS (
        SELECT
            municipality_key,
            json_group_array(json_object(
                'tech_type', tech_type,
                'unit_count', unit_count,
                'capacity_mw', capacity_mw
            )) AS tech_mix
        FROM municipality_technology
        GROUP BY municipality_key
    ),
    -- TODO: Populate data/municipality_metrics.csv with official area/population values for density calculations.
    municipality_totals AS (
        SELECT
            current_units.municipality_key,
            municipality_name,
            county,
            state,
            COUNT(*) AS unit_count,
            SUM(capacity_mw)::DOUBLE AS capacity_mw,
            COALESCE(SUM(capacity_mw)::DOUBLE / NULLIF(MAX(TRY_CAST(metrics.area_km2 AS DOUBLE)), 0), SUM(capacity_mw)::DOUBLE) AS capacity_density_mw_per_km2
        FROM current_units
        LEFT JOIN read_csv('data/municipality_metrics.csv', header = true, columns = {municipality_key: 'VARCHAR', area_km2: 'DOUBLE', population: 'DOUBLE'}) AS metrics
            ON current_units.municipality_key = metrics.municipality_key
        WHERE municipality_name IS NOT NULL AND current_units.municipality_key IS NOT NULL
        GROUP BY current_units.municipality_key, municipality_name, county, state
    ),
    top_municipalities AS (
        SELECT
            municipality_totals.*,
            municipality_tech_mix.tech_mix
        FROM municipality_totals
        LEFT JOIN municipality_tech_mix USING (municipality_key)
        ORDER BY capacity_mw DESC
        LIMIT 100
    ),
    solar_size_distribution AS (
        SELECT
            CASE
                WHEN capacity_mw < 0.01 THEN '< 10 kW'
                WHEN capacity_mw < 0.1 THEN '10–100 kW'
                WHEN capacity_mw < 1 THEN '100 kW–1 MW'
                ELSE '≥ 1 MW'
            END AS size_band,
            CASE
                WHEN capacity_mw < 0.01 THEN 1
                WHEN capacity_mw < 0.1 THEN 2
                WHEN capacity_mw < 1 THEN 3
                ELSE 4
            END AS sort_order,
            COUNT(*) AS unit_count,
            SUM(capacity_mw)::DOUBLE AS capacity_mw
        FROM current_units
        WHERE tech_type = 'Solar' AND capacity_mw IS NOT NULL
        GROUP BY size_band, sort_order
    ),
    storage_locations AS (
        SELECT DISTINCT municipality_key, operator_name
        FROM current_units
        WHERE tech_type IN ('Storage', 'Gas Storage')
          AND municipality_key IS NOT NULL
          AND operator_name IS NOT NULL
    ),
    solar_storage_attach AS (
        SELECT
            COUNT(*) AS solar_unit_count,
            COUNT(*) FILTER (WHERE municipality_key IS NOT NULL AND operator_name IS NOT NULL) AS eligible_solar_unit_count,
            COUNT(*) FILTER (WHERE EXISTS (
                SELECT 1
                FROM storage_locations
                WHERE storage_locations.municipality_key = solar.municipality_key
                  AND storage_locations.operator_name = solar.operator_name
            )) AS matched_solar_unit_count
        FROM current_units AS solar
        WHERE tech_type = 'Solar'
    ),
    data_quality_by_technology AS (
        SELECT
            tech_type,
            COUNT(*) AS total_units,
            COUNT(*) FILTER (WHERE lat IS NOT NULL AND lon IS NOT NULL) AS exact_coordinate_units,
            COUNT(*) FILTER (WHERE lat IS NULL AND lon IS NULL AND municipality_name IS NOT NULL) AS municipality_only_units,
            COUNT(*) FILTER (WHERE lat IS NULL AND lon IS NULL AND municipality_name IS NULL) AS no_location_units,
            CASE WHEN COUNT(*) = 0 THEN 0.0 ELSE COUNT(*) FILTER (WHERE lat IS NOT NULL AND lon IS NOT NULL) * 100.0 / COUNT(*) END AS exact_coordinate_percentage
        FROM current_units
        GROUP BY tech_type
    ),
    data_quality AS (
        SELECT
            COUNT(*) AS total_units,
            COUNT(*) FILTER (WHERE lat IS NOT NULL AND lon IS NOT NULL) AS exact_coordinate_units,
            COUNT(*) FILTER (WHERE lat IS NULL AND lon IS NULL AND municipality_name IS NOT NULL) AS municipality_only_units,
            COUNT(*) FILTER (WHERE lat IS NULL AND lon IS NULL AND municipality_name IS NULL) AS no_location_units,
            CASE WHEN COUNT(*) = 0 THEN 0.0 ELSE COUNT(*) FILTER (WHERE lat IS NOT NULL AND lon IS NOT NULL) * 100.0 / COUNT(*) END AS exact_coordinate_percentage,
            CASE WHEN COUNT(*) = 0 THEN 0.0 ELSE COUNT(*) FILTER (WHERE lat IS NULL AND lon IS NULL AND municipality_name IS NOT NULL) * 100.0 / COUNT(*) END AS municipality_only_percentage
        FROM current_units
    )
    SELECT
        current_timestamp::VARCHAR AS generated_at,
        (
            SELECT COALESCE(json_group_array(json_object(
                'tech_type', tech_type,
                'status', status,
                'unit_count', unit_count,
                'capacity_mw', capacity_mw
            )), '[]'::JSON)
            FROM technology_status
        ) AS total_capacity_mw,
        (
            SELECT COALESCE(json_group_array(json_object(
                'week', week,
                'tech_type', tech_type,
                'status', status,
                'unit_count', unit_count,
                'delta_units', delta_units,
                'capacity_mw', capacity_mw,
                'delta_mw', delta_mw
            )), '[]'::JSON)
            FROM weekly_delta
        ) AS weekly_delta,
        (
            SELECT COALESCE(json_group_array(json_object(
                'municipality_key', municipality_key,
                'municipality_name', municipality_name,
                'county', county,
                'state', state,
                'unit_count', unit_count,
                'capacity_mw', capacity_mw,
                'capacity_density_mw_per_km2', capacity_density_mw_per_km2,
                'tech_mix', tech_mix
            )), '[]'::JSON)
            FROM top_municipalities
        ) AS top_municipalities,
        (
            SELECT COALESCE(json_group_array(json_object(
                'size_band', size_band,
                'unit_count', unit_count,
                'capacity_mw', capacity_mw
            )), '[]'::JSON)
            FROM (SELECT * FROM solar_size_distribution ORDER BY sort_order)
        ) AS solar_size_distribution,
        (
            SELECT json_object(
                'total_units', data_quality.total_units,
                'exact_coordinate_units', data_quality.exact_coordinate_units,
                'municipality_only_units', data_quality.municipality_only_units,
                'no_location_units', data_quality.no_location_units,
                'exact_coordinate_percentage', data_quality.exact_coordinate_percentage,
                'municipality_only_percentage', data_quality.municipality_only_percentage,
                'by_technology', (
                    SELECT COALESCE(json_group_array(json_object(
                        'tech_type', tech_type,
                        'total_units', total_units,
                        'exact_coordinate_units', exact_coordinate_units,
                        'municipality_only_units', municipality_only_units,
                        'no_location_units', no_location_units,
                        'exact_coordinate_percentage', exact_coordinate_percentage
                    )), '[]'::JSON)
                    FROM (SELECT * FROM data_quality_by_technology ORDER BY total_units DESC)
                )
            )
            FROM data_quality
        ) AS data_quality,
        (
            SELECT json_object(
                'solar_unit_count', solar_unit_count,
                'eligible_solar_unit_count', eligible_solar_unit_count,
                'matched_solar_unit_count', matched_solar_unit_count,
                'eligible_match_percentage', CASE WHEN eligible_solar_unit_count = 0 THEN 0.0 ELSE matched_solar_unit_count * 100.0 / eligible_solar_unit_count END,
                'all_solar_match_percentage', CASE WHEN solar_unit_count = 0 THEN 0.0 ELSE matched_solar_unit_count * 100.0 / solar_unit_count END
            )
            FROM solar_storage_attach
        ) AS storage_attach_rate_proxy
) TO 'public/data/summary.json' (FORMAT JSON, ARRAY false);

-- Keep a compact append-only history keyed by ISO week, technology and status.
COPY (
    WITH current_week AS (
        SELECT
            strftime(current_date, '%G-W%V') AS week,
            tech_type,
            status,
            COUNT(*) AS unit_count,
            SUM(capacity_mw)::DOUBLE AS capacity_mw
        FROM current_units
        GROUP BY tech_type, status
    ),
    previous_history AS (
        SELECT week, tech_type, status, unit_count, capacity_mw
        FROM read_json('history.json', format = 'array', columns = {week: 'VARCHAR', tech_type: 'VARCHAR', status: 'VARCHAR', unit_count: 'BIGINT', capacity_mw: 'DOUBLE'}, union_by_name = true, ignore_errors = true, maximum_object_size = 100000000)
        WHERE week <> strftime(current_date, '%G-W%V')
    ),
    history AS (
        SELECT * FROM previous_history
        UNION ALL
        SELECT * FROM current_week
    )
    SELECT week, tech_type, status, unit_count, capacity_mw
    FROM history
    ORDER BY week, tech_type, status
) TO 'history.json' (FORMAT JSON, ARRAY true);
