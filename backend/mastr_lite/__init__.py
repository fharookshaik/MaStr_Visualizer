"""
open-MaStR Lite - Lightweight MaStR data processor for PostgreSQL

A streamlined version of open-MaStR that processes pre-downloaded
MaStR zip files and loads them into PostgreSQL databases.
"""

from .main import MaStrProcessor
from .utils.db import DBConfig, DBHelper
from .utils.download_mastr import MaStrDownloader


__version__ = "0.1.0"
__all__ = [
    "MaStrProcessor",
    "DBConfig",
    "MaStrDownloader",
    "DBHelper"
    ]
