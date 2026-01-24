"""
Main LiteMastr class for processing MaStR data.
"""

from pathlib import Path
from typing import List, Optional

from .utils.db import DBConfig, DBHelper
from .utils.logger import setup_logging
from .utils.xml_processor import process_zip_to_database
from .utils.orm import Base


class MaStrProcessor:
    """
    Lightweight MaStR data processor for PostgreSQL.

    Processes pre-downloaded MaStR zip files and loads them into PostgreSQL databases.

    Parameters
    ----------
    config_file : str
        Path to YAML configuration file containing PostgreSQL connection details

    Example
    -------
    >>> mastr_lite = LiteMastr('')
    >>> mastr_lite.process_zip('Gesamtdatenexport_20230101.zip')
    """
    def __init__(self, db_config : DBConfig) -> None:
        self.db_config = db_config
        self.engine = None
        self._config = None

        # Create database engine
        self._create_engine()

        # Create all tables
        Base.metadata.create_all(self.engine)

    def _create_engine(self):
        """Create PostgreSQL database engine."""
        db_helper = DBHelper(self.db_config)
        self.engine = db_helper.get_engine()
    
    def process_zip(
        self,
        zip_file_path: str,
        data: Optional[List[str]] = None,
        bulk_cleansing: bool = True
    ) -> None:
        """
        Process MaStR zip file and load into database.

        Parameters
        ----------
        zip_file_path : str
            Path to the MaStR XML zip file
        data : List[str], optional
            List of data types to process (e.g., ['wind', 'solar']).
            If None, processes all available data types.
        bulk_cleansing : bool, optional
            Whether to apply data cleansing (recommended), by default True

        Raises
        ------
        FileNotFoundError
            If zip file doesn't exist
        ValueError
            If zip file is invalid
        """
        zip_path = Path(zip_file_path)

        if not zip_path.exists():
            raise FileNotFoundError(f"Zip file not found: {zip_file_path}")

        if not zip_path.suffix.lower() == '.zip':
            raise ValueError(f"File must be a zip file: {zip_file_path}")

        # Process the zip file
        process_zip_to_database(
            engine=self.engine,
            zipped_xml_file_path=str(zip_path),
            data=data,
            bulk_cleansing=bulk_cleansing
        )