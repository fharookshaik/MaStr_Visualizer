"""
XML processing logic for MaStR lite.
Adapted from open-mastr xml_download utils.
"""

import os
from concurrent.futures import ProcessPoolExecutor, wait
from io import StringIO
from multiprocessing import cpu_count
from zipfile import ZipFile

import re
import lxml
import numpy as np
import pandas as pd
import sqlalchemy
from sqlalchemy import inspect
from sqlalchemy.sql import text
from sqlalchemy.sql.sqltypes import Date, DateTime

from .logger import setup_logger
from .helpers import data_to_include_tables
from .orm import tablename_mapping
from .utils_cleansing_bulk import cleanse_bulk_data

log = setup_logger()


def process_zip_to_database(
    engine: sqlalchemy.engine.Engine,
    zipped_xml_file_path: str,
    data: list = None,
    bulk_cleansing: bool = True,
) -> None:
    """
    Process MaStR XML zip file and write to database.

    Parameters
    ----------
    engine : sqlalchemy.engine.Engine
        Database engine (PostgreSQL only)
    zipped_xml_file_path : str
        Path to the MaStR XML zip file
    data : list, optional
        List of data types to process. If None, processes all.
    bulk_cleansing : bool, optional
        Whether to apply data cleansing, by default True
    """
    log.info("Starting MaStR lite processing...")

    if data is None:
        from .constants import BULK_DATA
        data = BULK_DATA

    include_tables = data_to_include_tables(data, mapping="write_xml")
    threads_data = []

    with ZipFile(zipped_xml_file_path, "r") as f:
        files_list = correct_ordering_of_filelist(f.namelist())

        for file_name in files_list:
            xml_table_name = extract_xml_table_name(file_name)

            if not is_table_relevant(xml_table_name, include_tables):
                continue

            sql_table_name = extract_sql_table_name(xml_table_name)
            threads_data.append(
                (
                    file_name,
                    xml_table_name,
                    sql_table_name,
                    str(engine.url),
                    engine.url.password,
                    zipped_xml_file_path,
                    bulk_cleansing,
                )
            )

    interleaved_files = interleave_files(threads_data)
    number_of_processes = get_number_of_processes()

    if number_of_processes > 0:
        with ProcessPoolExecutor(max_workers=number_of_processes) as executor:
            futures = [
                executor.submit(process_xml_file, *item) for item in interleaved_files
            ]
            for future in futures:
                future.result()
            wait(futures)
    else:
        for item in interleaved_files:
            process_xml_file(*item)

    log.info("MaStR lite processing completed successfully.")


def get_number_of_processes():
    """Get the number of processes to use for processing."""
    if "NUMBER_OF_PROCESSES" in os.environ:
        try:
            number_of_processes = int(os.environ.get("NUMBER_OF_PROCESSES"))
        except ValueError:
            log.warning("Invalid value for NUMBER_OF_PROCESSES. Fallback to 1.")
            return 1
        if number_of_processes >= cpu_count():
            log.warning(
                f"Your system supports {cpu_count()} CPUs. Using "
                f"more processes than available CPUs may cause excessive "
                f"context-switching overhead."
            )
        return number_of_processes
    if "USE_RECOMMENDED_NUMBER_OF_PROCESSES" in os.environ:
        return int(min(cpu_count() - 1, 4))
    return -1


def process_xml_file(
    file_name: str,
    xml_table_name: str,
    sql_table_name: str,
    connection_url: str,
    password: str,
    zipped_xml_file_path: str,
    bulk_cleansing: bool,
) -> None:
    """Process a single xml file and write it to the database."""
    try:
        # Handle password obfuscation in connection URL
        if password:
            connection_url = re.sub(
                r"://([^:]+):\*+@", r"://\1:" + password + "@", connection_url
            )

        # Create efficient engine for PostgreSQL
        engine = create_efficient_engine(connection_url)

        with ZipFile(zipped_xml_file_path, "r") as f:
            log.info(f"Processing file '{file_name}'...")
            if is_first_file(file_name):
                log.info(f"Creating table '{sql_table_name}'...")
                create_database_table(engine, xml_table_name)

            df = read_xml_file(f, file_name)
            df = process_table_before_insertion(
                df,
                xml_table_name,
                zipped_xml_file_path,
                bulk_cleansing,
            )

            # Use PostgreSQL-specific insertion
            add_table_to_postgres_database(df, xml_table_name, sql_table_name, engine)

    except Exception as e:
        log.error(f"Error processing file '{file_name}': '{e}'")


def create_efficient_engine(connection_url: str) -> sqlalchemy.engine.Engine:
    """Create an efficient engine for PostgreSQL."""
    from sqlalchemy import create_engine

    return create_engine(
        connection_url,
        connect_args={
            "connect_timeout": 300,  # Wait for max 5 minutes before timing out
        },
        pool_pre_ping=True,  # Verify connections before use
        pool_size=10,  # Max number of connections in the pool
        max_overflow=20,  # Create up to 20 more connections when demand is high
        pool_recycle=180,  # Recycle inactive connections after 180 seconds
        pool_timeout=30,  # Wait for 30 seconds before raising exception when pool is full
    )


def interleave_files(threads_data: list):
    """Interleave files to reduce database lock conflicts."""
    files_grouped_by_table = {}

    for item in threads_data:
        table_name = item[2]
        if table_name not in files_grouped_by_table:
            files_grouped_by_table[table_name] = []
        files_grouped_by_table[table_name].append(item)

    sorted_threads_data = []
    max_no_files_per_table = max(
        len(group) for group in files_grouped_by_table.values()
    )

    for idx in range(max_no_files_per_table):
        for table_name in files_grouped_by_table.keys():
            files = files_grouped_by_table[table_name]
            if idx < len(files):
                sorted_threads_data.append(files[idx])

    return sorted_threads_data


def extract_xml_table_name(file_name: str) -> str:
    """Extract the XML table name from the file name."""
    return file_name.split("_")[0].split(".")[0].lower()


def extract_sql_table_name(xml_table_name: str) -> str:
    """Extract the SQL table name from the xml table name."""
    return tablename_mapping[xml_table_name]["__name__"]


def is_table_relevant(xml_table_name: str, include_tables: list) -> bool:
    """Check if the table contains relevant data."""
    try:
        boolean_write_table_to_sql_database = (
            tablename_mapping[xml_table_name]["__class__"] is not None
        )
    except KeyError:
        log.warning(
            f"Table '{xml_table_name}' is not supported and will be skipped."
        )
        return False

    include_count = include_tables.count(xml_table_name)
    return include_count == 1 and boolean_write_table_to_sql_database


def create_database_table(
    engine: sqlalchemy.engine.Engine, xml_table_name: str
) -> None:
    """Create database table for the given XML table name."""
    orm_class = tablename_mapping[xml_table_name]["__class__"]
    orm_class.__table__.drop(engine, checkfirst=True)
    orm_class.__table__.create(engine)


def is_first_file(file_name: str) -> bool:
    """Check if the file name indicates it's the first file from the table."""
    return (
        file_name.split(".")[0].split("_")[-1] == "1"
        or len(file_name.split(".")[0].split("_")) == 1
    )


def cast_date_columns_to_datetime(
    xml_table_name: str, df: pd.DataFrame
) -> pd.DataFrame:
    """Convert date columns to datetime."""
    sqlalchemy_columnlist = tablename_mapping[xml_table_name][
        "__class__"
    ].__table__.columns.items()
    for column in sqlalchemy_columnlist:
        column_name = column[0]
        if is_date_column(column, df):
            df[column_name] = pd.to_datetime(df[column_name], errors="coerce")
    return df


def is_date_column(column, df: pd.DataFrame) -> bool:
    """Check if column is a date/datetime column."""
    return type(column[1].type) in [Date, DateTime] and column[0] in df.columns


def correct_ordering_of_filelist(files_list: list) -> list:
    """Correct file ordering for proper processing."""
    files_list_ordered = []
    count_if_zeros_are_prefixed = 0
    for file_name in files_list:
        if len(file_name.split(".")[0].split("_")[-1]) == 1:
            file_name = file_name.split("_")[0] + "_0" + file_name.split("_")[1]
            count_if_zeros_are_prefixed += 1
        files_list_ordered.append(file_name)

    files_list_ordered.sort()
    files_list_correct = []
    for file_name in files_list_ordered:
        if file_name.split(".")[0].split("_")[-1][0] == "0":
            file_name = file_name.split("_")[0] + "_" + file_name.split("_0")[-1]
        files_list_correct.append(file_name)

    if count_if_zeros_are_prefixed >= 5:
        files_list = files_list_correct

    return files_list


def read_xml_file(f: ZipFile, file_name: str) -> pd.DataFrame:
    """Read XML file from zip and return as DataFrame."""
    with f.open(file_name) as xml_file:
        try:
            return pd.read_xml(xml_file, encoding="UTF-16", parser="etree")
        except lxml.etree.XMLSyntaxError as error:
            return handle_xml_syntax_error(xml_file.read().decode("utf-16"), error)


def change_column_names_to_orm_format(
    df: pd.DataFrame, xml_table_name: str
) -> pd.DataFrame:
    """Change column names to match ORM format."""
    if tablename_mapping[xml_table_name]["replace_column_names"]:
        df.rename(
            columns=tablename_mapping[xml_table_name]["replace_column_names"],
            inplace=True,
        )
    return df


def add_table_to_postgres_database(
    df: pd.DataFrame,
    xml_table_name: str,
    sql_table_name: str,
    engine: sqlalchemy.engine.Engine,
) -> None:
    """Add data to PostgreSQL database table."""
    # Get data types dictionary
    table_columns_list = list(
        tablename_mapping[xml_table_name]["__class__"].__table__.columns
    )
    dtypes_for_writing_sql = {
        column.name: column.type
        for column in table_columns_list
        if column.name in df.columns
    }

    # Convert date columns to datetime
    df = cast_date_columns_to_datetime(xml_table_name, df)

    # Add missing columns to table
    add_missing_columns_to_table(
        engine, xml_table_name, column_list=df.columns.tolist()
    )

    # Attempt to insert data
    for _ in range(10000):
        try:
            with engine.connect() as con:
                with con.begin():
                    df.to_sql(
                        sql_table_name,
                        con=con,
                        index=False,
                        if_exists="append",
                        dtype=dtypes_for_writing_sql,
                    )
                    break

        except sqlalchemy.exc.DataError as err:
            delete_wrong_xml_entry(err, df)

        except sqlalchemy.exc.IntegrityError:
            # Handle unique constraint violations
            df = write_single_entries_until_not_unique_comes_up(
                df, xml_table_name, engine
            )


def add_zero_as_first_character_for_too_short_string(df: pd.DataFrame) -> pd.DataFrame:
    """Add leading zeros to short strings that should be zero-padded."""
    dict_of_columns_and_string_length = {
        "Gemeindeschluessel": 8,
        "Postleitzahl": 5,
    }
    for column_name, string_length in dict_of_columns_and_string_length.items():
        if column_name not in df.columns:
            continue
        try:
            df[column_name] = df[column_name].astype("Int64").astype(str)
        except (ValueError, TypeError):
            df[column_name] = df[column_name].astype(str)
            continue
        df[column_name] = df[column_name].where(
            cond=-df[column_name].isin(["None", "<NA>"]), other=None
        )

        string_adding_series = pd.Series(["0"] * len(df))
        string_adding_series = string_adding_series.where(
            cond=df[column_name].str.len() == string_length - 1, other=""
        )
        df[column_name] = string_adding_series + df[column_name]
    return df


def write_single_entries_until_not_unique_comes_up(
    df: pd.DataFrame, xml_table_name: str, engine: sqlalchemy.engine.Engine
) -> pd.DataFrame:
    """Remove duplicate entries based on primary key."""
    from sqlalchemy import select

    table = tablename_mapping[xml_table_name]["__class__"].__table__
    primary_key = next(c for c in table.columns if c.primary_key)

    with engine.connect() as con:
        with con.begin():
            key_list = (
                pd.read_sql(sql=select(primary_key), con=con).values.squeeze().tolist()
            )

    len_df_before = len(df)
    df = df.drop_duplicates(subset=[primary_key.name])
    df = df.set_index(primary_key.name)
    df = df.drop(labels=key_list, errors="ignore")
    df = df.reset_index()
    log.warning(f"{len_df_before - len(df)} entries already existed in the database.")

    return df


def add_missing_columns_to_table(
    engine: sqlalchemy.engine.Engine,
    xml_table_name: str,
    column_list: list,
) -> None:
    """Add missing columns to existing database table."""
    inspector = sqlalchemy.inspect(engine)
    table_name = tablename_mapping[xml_table_name]["__class__"].__table__.name
    columns = inspector.get_columns(table_name)
    column_names_from_database = [column["name"] for column in columns]

    missing_columns = set(column_list) - set(column_names_from_database)

    for column_name in missing_columns:
        if not column_exists(engine, table_name, column_name):
            alter_query = f'ALTER TABLE "{table_name}" ADD "{column_name}" VARCHAR NULL;'
            try:
                with engine.connect().execution_options(autocommit=True) as con:
                    with con.begin():
                        con.execute(text(alter_query))
            except sqlalchemy.exc.OperationalError as err:
                if "duplicate column name" not in str(err).lower():
                    raise err
            log.info(
                f"Added new column: {table_name}.{column_name}"
            )


def delete_wrong_xml_entry(err, df: pd.DataFrame) -> pd.DataFrame:
    """Delete problematic entries from DataFrame."""
    delete_entry = str(err).split("«")[0].split("»")[1]
    log.warning(f"The entry {delete_entry} was deleted due to its false data type.")
    return df.replace(delete_entry, np.nan)


def handle_xml_syntax_error(data: str, err) -> pd.DataFrame:
    """Handle XML syntax errors by removing problematic entries."""
    def find_nearest_brackets(xml_string: str, position: int):
        left_bracket_position = xml_string.rfind(">", 0, position)
        right_bracket_position = xml_string.find("<", position)
        return left_bracket_position, right_bracket_position

    data = data.splitlines()

    for _ in range(100):
        wrong_char_row, wrong_char_column = err.position
        row_with_error = data[wrong_char_row - 1]

        left_bracket, right_bracket = find_nearest_brackets(
            row_with_error, wrong_char_column
        )
        data[wrong_char_row - 1] = (
            row_with_error[: left_bracket + 1] + row_with_error[right_bracket:]
        )
        try:
            log.warning("One invalid xml expression was deleted.")
            df = pd.read_xml(StringIO("\n".join(data)))
            return df
        except lxml.etree.XMLSyntaxError as e:
            err = e
            continue

    raise Exception("An error occurred when parsing the xml file. Maybe it is corrupted?")


def process_table_before_insertion(
    df: pd.DataFrame,
    xml_table_name: str,
    zipped_xml_file_path: str,
    bulk_cleansing: bool,
) -> pd.DataFrame:
    """Process table data before database insertion."""
    df = add_zero_as_first_character_for_too_short_string(df)
    df = change_column_names_to_orm_format(df, xml_table_name)

    # Add metadata columns
    df["DatenQuelle"] = "bulk"
    df["DatumDownload"] = pd.Timestamp.now().strftime("%Y%m%d")

    if bulk_cleansing:
        df = cleanse_bulk_data(df, zipped_xml_file_path)

    return df


def column_exists(engine, table_name, column_name):
    """Check if column exists in table."""
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns
