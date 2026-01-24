"""
Database connection logic for PostgreSQL.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dataclasses import dataclass

import logging

log = logging.getLogger(__name__)

@dataclass
class DBConfig:
    DB_HOST : str | None
    DB_PORT : str | None
    DB_NAME : str | None
    DB_USER : str | None
    DB_PASSWORD : str | None
    DB_SCHEMA : str | None


class DBHelper:
    def __init__(self, db_config : DBConfig) -> None:
        self.db_config = db_config
        self.engine = None

    def _getDBURL(self):
        return f"postgresql://{self.db_config.DB_USER}:{self.db_config.DB_PASSWORD}@{self.db_config.DB_HOST}:{self.db_config.DB_PORT}/{self.db_config.DB_NAME}"

    
    def _create_engine(self):
        try:
            self.engine = create_engine(
                self._getDBURL(),
                echo=False,
                pool_pre_ping=True,
                connect_args={
                    'options': f'-c search_path={self.db_config.DB_SCHEMA}'
                } if self.db_config.DB_SCHEMA != 'public' else {}
            )

            log.info(f"Created PostgreSQL engine for database: {self.db_config.DB_NAME} (schema: {self.db_config.DB_SCHEMA})")

        except Exception as e:
            print('Cannot Create DB Engine: ', e)
    
    def get_engine(self):
        if self.engine is None:
            self._create_engine()
        
        return self.engine
    
    # ------------------------------------------------------------------
    # 1. Enable PostGIS if not enabled
    # ------------------------------------------------------------------
    def enable_postgis(self) -> bool:
        """
        Tries to enable PostGIS.
        Returns True if available, False if not installed.
        """
        engine = self.get_engine()

        check_sql = """
        SELECT 1
        FROM pg_available_extensions
        WHERE name = 'postgis';
        """

        try:
            with engine.begin() as conn:
                available = conn.execute(text(check_sql)).scalar()

                if not available:
                    log.warning(
                        "PostGIS extension is NOT available on this PostgreSQL instance. "
                        "Skipping spatial features."
                    )
                    return False

                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                log.info("PostGIS extension enabled.")
                return True

        except Exception as e:
            log.warning(f"PostGIS check failed: {e}")
            return False

    # ------------------------------------------------------------------
    # 2. Create geometry + spatial index for tables with lat/lon columns
    # ------------------------------------------------------------------
    def create_geometry_indexes(self, srid: int = 4326):
        """
        - Looks for tables containing Laengengrad & Breitengrad
        - Adds geometry column 'geom' if missing
        - Populates geom only when both coords are NOT NULL
        - Creates GiST index on geom
        """

        engine = self.get_engine()
        
        # Abort early if PostGIS is missing
        with engine.begin() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'postgis';")
            ).scalar()

            if not exists:
                log.warning("PostGIS not enabled. Geometry indexes skipped.")
                return
        
        schema = self.db_config.DB_SCHEMA

        find_tables_sql = """
        SELECT table_name
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND column_name IN ('Laengengrad', 'Breitengrad')
        GROUP BY table_name
        HAVING COUNT(*) = 2;
        """

        with engine.begin() as conn:
            tables = conn.execute(
                text(find_tables_sql),
                {"schema": schema}
            ).fetchall()

            for (table_name,) in tables:
                geom_col = "geom"
                geom_idx = f"{table_name}_geom_idx"

                log.info(f"Processing table: {schema}.{table_name}")

                # 1. Add geometry column if not exists
                conn.execute(text(f"""
                    ALTER TABLE "{schema}"."{table_name}"
                    ADD COLUMN IF NOT EXISTS {geom_col} geometry(Point, {srid});
                """))

                # 2. Populate geometry only where coords exist
                conn.execute(text(f"""
                    UPDATE "{schema}"."{table_name}"
                    SET {geom_col} = ST_SetSRID(
                        ST_MakePoint("Laengengrad", "Breitengrad"),
                        {srid}
                    )
                    WHERE "Laengengrad" IS NOT NULL
                      AND "Breitengrad" IS NOT NULL
                      AND {geom_col} IS NULL;
                """))

                # 3. Create GiST index (NULL-safe by default)
                conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS "{geom_idx}"
                    ON "{schema}"."{table_name}"
                    USING GIST ({geom_col});
                """))

                log.info(
                    f"Geometry index ensured for {schema}.{table_name}"
                )


# class DBHelper:
#     def __init__(self, db_config : DBConfig = None) -> None:
#         self.db_config = db_config or self._getdbconfig()
#         self.engine = None

#     def _getDBURL(self):
#         return f"postgresql://{self.db_config.DB_USER}:{self.db_config.DB_PASSWORD}@{self.db_config.DB_HOST}:{self.db_config.DB_PORT}/{self.db_config.DB_NAME}"

#     def _getdbconfig(self):
#         try:
#             if load_dotenv():
#                 return DBConfig(
#                     DB_HOST=os.getenv('POSTGRES_DB'),
#                     DB_PORT=os.getenv('POSTGRES_PORT'),
#                     DB_NAME=os.getenv('POSTGRES_NAME'),
#                     DB_USER=os.getenv('POSTGRES_USER'),
#                     DB_PASSWORD=os.getenv('DB_PASSWORD')
#                 )
#             else:
#                 raise EnvironmentError('Environment file not found')
#         except Exception as e:
#             print('Error fetching DB details: ', e)
    
#     def _create_engine(self):
#         try:
#             self.engine = create_engine(
#                 self._getDBURL(),
#                 echo=False,
#                 pool_pre_ping=True,
#             )
#         except Exception as e:
#             print('Cannot Create DB Engine: ', e)
    
#     def get_engine(self):
#         if self.engine is None:
#             self._create_engine()
        
#         return self.engine