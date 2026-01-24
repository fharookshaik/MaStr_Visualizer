import os
import sys
import zipfile
from pathlib import Path
from dotenv import load_dotenv
from logger import logger

from mastr_lite import DBConfig, MaStrDownloader, MaStrProcessor, DBHelper


WORK_DIR = Path(__file__).resolve().parent
PROJECT_DIR = WORK_DIR / ".MaStr"
DOWNLOADS_DIR = PROJECT_DIR / "xml_downloads"

os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def getdb_config(db_host=None, db_port=None, db_name=None, db_user=None, db_pass=None, db_schema=None):
    try:
        # Load env if needed
        if any(v is None for v in [db_host, db_port, db_name, db_user, db_pass, db_schema]):
            if not load_dotenv():
                raise EnvironmentError("Environment file not found")

        DB_HOST = db_host or os.getenv("DB_HOST")
        DB_PORT = db_port or os.getenv("DB_PORT")
        DB_NAME = db_name or os.getenv("DB_NAME")
        DB_USER = db_user or os.getenv("DB_USER")
        DB_PASSWORD = db_pass or os.getenv("DB_PASSWORD")
        DB_SCHEMA = db_schema or os.getenv("DB_SCHEMA")

        missing = [
            name for name, value in {
                "DB_HOST": DB_HOST,
                "DB_PORT": DB_PORT,
                "DB_NAME": DB_NAME,
                "DB_USER": DB_USER,
                "DB_PASSWORD": DB_PASSWORD,
                "DB_SCHEMA": DB_SCHEMA,
            }.items()
            if value is None
        ]

        if missing:
            raise ValueError(f"Missing DB config values: {', '.join(missing)}")

        return DBConfig(
            DB_HOST=DB_HOST,
            DB_PORT=DB_PORT,
            DB_NAME=DB_NAME,
            DB_USER=DB_USER,
            DB_PASSWORD=DB_PASSWORD,
            DB_SCHEMA=DB_SCHEMA,
        )

    except Exception as e:
        raise RuntimeError(f"Error fetching DB details: {e}") from e


def find_existing_zip(download_dir: Path):
    zips = sorted(download_dir.glob("*.zip"), key=os.path.getmtime, reverse=True)
    return zips[0] if zips else None


def is_valid_zip(zip_path: Path) -> bool:
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            bad_file = zf.testzip()
            if bad_file is not None:
                logger.warning(f"Corrupt file inside ZIP: {bad_file}")
                return False
        return True
    except zipfile.BadZipFile:
        logger.warning("BadZipFile detected.")
        return False
    except Exception as e:
        logger.warning(f"ZIP integrity check failed: {e}")
        return False


def main(use_existing_if_available=True):
    logger.info("Starting MaStR Orchestrator...")

    # 1️⃣ Load DB config
    db_config = getdb_config()

    # 2️⃣ Find existing ZIP (optional)
    zip_file = None
    if use_existing_if_available:
        zip_file = find_existing_zip(DOWNLOADS_DIR)
        if zip_file:
            logger.info(f"Found existing ZIP: {zip_file}")

            if not is_valid_zip(zip_file):
                logger.warning("Existing ZIP is corrupt. Deleting and re-downloading...")
                try:
                    zip_file.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete corrupt ZIP: {e}")
                zip_file = None
            else:
                logger.info("Existing ZIP passed integrity check.")

    # 3️⃣ Download if needed
    if not zip_file:
        logger.info("No valid ZIP found. Downloading latest...")
        try:
            zip_file = MaStrDownloader(output_dir=str(DOWNLOADS_DIR))
            logger.info(f"Downloaded successfully: {zip_file}")
        except Exception as e:
            raise RuntimeError(f"Download failed: {e}") from e

    # 4️⃣ Process ZIP
    logger.info("Starting processing...")
    try:
        mastr_lite = MaStrProcessor(db_config=db_config)
        mastr_lite.process_zip(
            zip_file_path=str(zip_file),
            bulk_cleansing=True,
            # data=['wind']
        )
    except Exception as e:
        raise RuntimeError(f"Processing failed: {e}") from e

    # ------------------------------------------------------------------
    # 5️⃣ Enable PostGIS + create spatial indexes
    # ------------------------------------------------------------------
    logger.info("Enabling PostGIS and creating geometry indexes...")

    try:
        db_helper = DBHelper(db_config=db_config)
        postgis_enabled = db_helper.enable_postgis()
        if postgis_enabled:
            db_helper.create_geometry_indexes(srid=4326)
        else:
            logger.warning("Spatial features disabled (PostGIS not available).")
    except Exception as e:
        raise RuntimeError(f"PostGIS / spatial index step failed: {e}") from e

    logger.info("MaStR pipeline completed successfully.")


if __name__ == "__main__":
    try:
        main(use_existing_if_available=True)
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
