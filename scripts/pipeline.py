#!/usr/bin/env python3
# MIT License
# Copyright (c) 2026 MaStR Visualizer contributors

"""Stream MaStR generation units from the official ZIP export into Parquet."""

from __future__ import annotations

import argparse
import logging
import re
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterable, Iterator

import pyarrow as pa
import pyarrow.parquet as pq
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "public" / "data" / "units.parquet"
DOWNLOAD_PAGE = "https://www.marktstammdatenregister.de/MaStR/Datendownload"
DOWNLOAD_BASE = "https://download.marktstammdatenregister.de/"
CHUNK_SIZE = 100_000
LOG = logging.getLogger("mastr.pipeline")

SCHEMA = pa.schema(
    [
        pa.field("mastr_id", pa.string(), nullable=False),
        pa.field("tech_type", pa.string()),
        pa.field("capacity_mw", pa.float32()),
        pa.field("status", pa.string()),
        pa.field("lat", pa.float32()),
        pa.field("lon", pa.float32()),
        pa.field("municipality_key", pa.string()),
        pa.field("municipality_name", pa.string()),
        pa.field("county", pa.string()),
        pa.field("state", pa.string()),
        pa.field("commissioning_date", pa.date32()),
        pa.field("operator_name", pa.string()),
    ]
)

UNIT_TAGS = {
    "EinheitBiomasse": "Biomass",
    "EinheitGasErzeuger": "Gas",
    "EinheitGasSpeicher": "Gas Storage",
    "EinheitGeothermieGrubengasDruckentspannung": "Geothermal",
    "EinheitKernkraft": "Nuclear",
    "EinheitSolar": "Solar",
    "EinheitStromSpeicher": "Storage",
    "EinheitVerbrennung": "Thermal",
    "EinheitWasser": "Hydro",
    "EinheitWind": "Wind",
}

FAMILY_TAGS = {
    "einheitenbiomasse": "EinheitBiomasse",
    "einheitengaserzeuger": "EinheitGasErzeuger",
    "einheitengasspeicher": "EinheitGasSpeicher",
    "einheitengeothermiegrubengasdruckentspannung": "EinheitGeothermieGrubengasDruckentspannung",
    "einheitenkernkraft": "EinheitKernkraft",
    "einheitensolar": "EinheitSolar",
    "einheitenstromspeicher": "EinheitStromSpeicher",
    "einheitenverbrennung": "EinheitVerbrennung",
    "einheitenwasser": "EinheitWasser",
    "einheitenwind": "EinheitWind",
}

STATUS_IDS = {"31": "Geplant", "35": "In Betrieb", "37": "Stillgelegt", "38": "Stillgelegt"}
ENERGY_TYPES = {
    "2403": "Geothermal",
    "2404": "Solar",
    "2405": "Thermal",
    "2406": "Gas",
    "2407": "Thermal",
    "2408": "Thermal",
    "2409": "Thermal",
    "2410": "Gas",
    "2411": "Gas",
    "2412": "Thermal",
    "2413": "Thermal",
    "2493": "Biomass",
    "2494": "Nuclear",
    "2495": "Solar",
    "2496": "Storage",
    "2497": "Wind",
    "2498": "Hydro",
}
STATE_NAMES = {
    "1400": "Brandenburg",
    "1401": "Berlin",
    "1402": "Baden-Württemberg",
    "1403": "Bayern",
    "1404": "Bremen",
    "1405": "Hessen",
    "1406": "Hamburg",
    "1407": "Mecklenburg-Vorpommern",
    "1408": "Niedersachsen",
    "1409": "Nordrhein-Westfalen",
    "1410": "Rheinland-Pfalz",
    "1411": "Schleswig-Holstein",
    "1412": "Saarland",
    "1413": "Sachsen",
    "1414": "Sachsen-Anhalt",
    "1415": "Thüringen",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--zip", type=Path, help="Local MaStR ZIP (default: newest archive in data/raw)")
    source.add_argument("--url", help="Explicit MaStR ZIP URL; defaults to the latest link on the official download page")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output Parquet path")
    parser.add_argument("--limit", type=int, help="Stop after this many parsed units (smoke testing)")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help="Rows per Parquet write batch")
    parser.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero")
    if args.chunk_size < 1:
        parser.error("--chunk-size must be greater than zero")
    return args


def find_local_archive() -> Path | None:
    raw_dir = ROOT / "data" / "raw"
    archives = sorted(raw_dir.glob("Gesamtdatenexport_*.zip")) if raw_dir.exists() else []
    return archives[-1] if archives else None


def latest_download_url() -> str:
    request = urllib.request.Request(DOWNLOAD_PAGE, headers={"User-Agent": "MaStR-Visualizer/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        page = response.read().decode("utf-8", errors="replace")
    matches = re.findall(r"https://download\.marktstammdatenregister\.de/(Gesamtdatenexport_[^\"'<>\s]+\.zip)", page)
    if not matches:
        raise RuntimeError(f"No current Gesamtdatenexport ZIP link found on {DOWNLOAD_PAGE}")
    return urllib.parse.urljoin(DOWNLOAD_BASE, matches[0])


def open_archive(source: Path | str) -> zipfile.ZipFile:
    """Open a local archive or cache a remote download without extracting it."""
    if isinstance(source, Path):
        LOG.info("Using local export: %s", source)
        return zipfile.ZipFile(source)

    parsed = urllib.parse.urlparse(source)
    filename = Path(parsed.path).name or "mastr-export.zip"
    download_path = ROOT / ".cache" / filename
    download_path.parent.mkdir(parents=True, exist_ok=True)
    if not download_path.exists() or download_path.stat().st_size == 0:
        LOG.info("Downloading export to %s", download_path)
        temporary_path = download_path.with_suffix(download_path.suffix + ".part")
        try:
            with urllib.request.urlopen(source, timeout=120) as response, temporary_path.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            temporary_path.replace(download_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
    try:
        return zipfile.ZipFile(download_path)
    except zipfile.BadZipFile:
        download_path.unlink(missing_ok=True)
        LOG.warning("Cached download was not a valid ZIP; downloading again")
        temporary_path = download_path.with_suffix(download_path.suffix + ".part")
        try:
            with urllib.request.urlopen(source, timeout=120) as response, temporary_path.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            temporary_path.replace(download_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        return zipfile.ZipFile(download_path)


def local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


def child_text(record: etree._Element, name: str) -> str | None:
    for child in record:
        if local_name(child) == name:
            value = (child.text or "").strip()
            return value or None
    return None


def parse_float(value: str | None) -> float | None:
    if not value:
        return None
    normalized = value.strip().replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def member_sort_key(name: str) -> tuple[str, int]:
    match = re.match(r"^(.*?)(?:_(\d+))?\.xml$", name, re.IGNORECASE)
    return (match.group(1).lower(), int(match.group(2) or 0)) if match else (name.lower(), 0)


def unit_members(names: Iterable[str]) -> list[tuple[str, str]]:
    members = []
    for name in names:
        filename = Path(name).name
        if filename.lower().startswith("einheiten") and filename.lower().endswith(".xml"):
            members.append(filename)
    result = []
    for filename in sorted(members, key=member_sort_key):
        family = filename.lower().removesuffix(".xml").split("_")[0]
        tag = FAMILY_TAGS.get(family)
        if tag:
            result.append((filename, tag))
    return result


def iter_records(archive: zipfile.ZipFile, member: str, record_tag: str) -> Iterator[etree._Element]:
    with archive.open(member) as source:
        context = etree.iterparse(
            source,
            events=("end",),
            tag=record_tag,
            recover=True,
            huge_tree=True,
            resolve_entities=False,
            no_network=True,
        )
        for _, record in context:
            yield record
            record.clear()
            parent = record.getparent()
            if parent is not None:
                while record.getprevious() is not None:
                    del parent[0]


def load_lookups(archive: zipfile.ZipFile) -> tuple[dict[str, str], dict[str, str]]:
    names = {Path(name).name for name in archive.namelist()}
    categories: dict[str, str] = {}
    if "Katalogkategorien.xml" in names:
        for record in iter_records(archive, "Katalogkategorien.xml", "Katalogkategorie"):
            identifier = child_text(record, "Id")
            label = child_text(record, "Name")
            if identifier and label:
                categories[identifier] = label

    status_ids: dict[str, str] = dict(STATUS_IDS)
    states: dict[str, str] = dict(STATE_NAMES)
    if "Katalogwerte.xml" in names:
        for record in iter_records(archive, "Katalogwerte.xml", "Katalogwert"):
            identifier = child_text(record, "Id")
            category_id = child_text(record, "KatalogKategorieId")
            label = child_text(record, "Wert")
            category = categories.get(category_id or "")
            if identifier and label and category == "Betriebsstatus":
                status_ids[identifier] = "Stillgelegt" if label in {"Vorübergehend stillgelegt", "Endgültig stillgelegt"} else ("Geplant" if label == "In Planung" else label)
            elif identifier and label and category == "BundeslaenderEinheiten":
                states[identifier] = label
    return status_ids, states


def build_operator_index(archive: zipfile.ZipFile, database: sqlite3.Connection) -> int:
    """Build a disk-backed operator-name index to avoid a large in-memory map."""
    database.execute("CREATE TABLE operators (mastr_id TEXT PRIMARY KEY, name TEXT NOT NULL)")
    names = {Path(name).name for name in archive.namelist()}
    members = sorted(
        (name for name in names if re.fullmatch(r"Marktakteure(?:_\d+)?\.xml", name)),
        key=member_sort_key,
    )
    total = 0
    for member in members:
        LOG.info("Indexing operator names from %s", member)
        batch = []
        for record in iter_records(archive, member, "Marktakteur"):
            identifier = child_text(record, "MastrNummer")
            label = child_text(record, "Firmenname")
            if not label:
                first_name = child_text(record, "MarktakteurVorname")
                last_name = child_text(record, "MarktakteurNachname")
                label = " ".join(part for part in (first_name, last_name) if part) or None
            if identifier and label:
                batch.append((identifier, label))
            if len(batch) >= 10_000:
                database.executemany("INSERT OR REPLACE INTO operators VALUES (?, ?)", batch)
                database.commit()
                total += len(batch)
                batch.clear()
        if batch:
            database.executemany("INSERT OR REPLACE INTO operators VALUES (?, ?)", batch)
            database.commit()
            total += len(batch)
    return total


def resolve_operator_names(database: sqlite3.Connection, rows: list[dict]) -> None:
    identifiers = {row["_operator_id"] for row in rows if row.get("_operator_id")}
    names: dict[str, str] = {}
    values = list(identifiers)
    for offset in range(0, len(values), 900):
        batch = values[offset : offset + 900]
        placeholders = ",".join("?" for _ in batch)
        names.update(database.execute(f"SELECT mastr_id, name FROM operators WHERE mastr_id IN ({placeholders})", batch))
    for row in rows:
        row["operator_name"] = names.get(row.pop("_operator_id", None))


def row_from_record(record: etree._Element, family: str, statuses: dict[str, str], states: dict[str, str]) -> dict:
    # Build one small field map per record; these XML rows may contain many columns.
    values = {
        local_name(child): (child.text or "").strip() or None
        for child in record
    }
    capacity_kw = parse_float(values.get("Bruttoleistung"))
    # MaStR power values are expressed in kW; convert to MW for the public schema.
    capacity_mw = capacity_kw / 1000 if capacity_kw is not None else None
    lat = parse_float(values.get("Breitengrad"))
    lon = parse_float(values.get("Laengengrad"))
    if lat is not None and not -90 <= lat <= 90:
        lat = None
    if lon is not None and not -180 <= lon <= 180:
        lon = None

    raw_state = values.get("Bundesland")
    return {
        "mastr_id": values.get("EinheitMastrNummer") or values.get("EinheitMaStRNummer"),
        "tech_type": ENERGY_TYPES.get(values.get("Energietraeger") or "", family),
        "capacity_mw": capacity_mw,
        "status": statuses.get(values.get("EinheitBetriebsstatus") or ""),
        "lat": lat,
        "lon": lon,
        "municipality_key": values.get("Gemeindeschluessel"),
        "municipality_name": values.get("Gemeinde"),
        "county": values.get("Landkreis"),
        "state": states.get(raw_state or "", raw_state),
        "commissioning_date": parse_date(values.get("Inbetriebnahmedatum")),
        "_operator_id": values.get("AnlagenbetreiberMastrNummer"),
    }


def flush_rows(rows: list[dict], writer: pq.ParquetWriter | None, output_path: Path, database: sqlite3.Connection) -> pq.ParquetWriter:
    resolve_operator_names(database, rows)
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    if writer is None:
        writer = pq.ParquetWriter(output_path, SCHEMA, compression="zstd", version="2.6")
    writer.write_table(table, row_group_size=len(rows))
    rows.clear()
    return writer


def write_pipeline(archive: zipfile.ZipFile, output_path: Path, limit: int | None, chunk_size: int) -> tuple[int, Counter]:
    members = unit_members(archive.namelist())
    if not members:
        raise RuntimeError("No supported generation-unit XML files found in the ZIP archive")
    LOG.info("Found %d unit XML members", len(members))
    statuses, states = load_lookups(archive)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)

    counts: Counter = Counter()
    total = 0
    rows: list[dict] = []
    writer: pq.ParquetWriter | None = None
    with tempfile.TemporaryDirectory(prefix="mastr-operators-") as temporary_dir:
        database = sqlite3.connect(Path(temporary_dir) / "operators.sqlite")
        try:
            if limit is None:
                indexed = build_operator_index(archive, database)
                LOG.info("Indexed %s operator names", f"{indexed:,}")
            else:
                database.execute("CREATE TABLE operators (mastr_id TEXT PRIMARY KEY, name TEXT NOT NULL)")
                LOG.info("Skipping full operator index for limited smoke test")

            for member, record_tag in members:
                LOG.info("Streaming %s (%s records)", member, record_tag)
                try:
                    for record in iter_records(archive, member, record_tag):
                        row = row_from_record(record, UNIT_TAGS[record_tag], statuses, states)
                        mastr_id = row.get("mastr_id")
                        if not mastr_id:
                            counts["skipped_missing_id"] += 1
                            continue
                        counts[row["tech_type"]] += 1
                        rows.append(row)
                        total += 1
                        if len(rows) >= chunk_size:
                            writer = flush_rows(rows, writer, output_path, database)
                            LOG.info("Wrote %s rows", f"{total:,}")
                        if limit is not None and total >= limit:
                            break
                except etree.XMLSyntaxError as exc:
                    LOG.warning("Recovered parse issue in %s: %s", member, exc)
                if limit is not None and total >= limit:
                    break

            if rows:
                writer = flush_rows(rows, writer, output_path, database)
            if writer is None:
                pq.write_table(pa.Table.from_pylist([], schema=SCHEMA), output_path, compression="zstd")
            return total, counts
        finally:
            if writer is not None:
                writer.close()
            database.close()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s")
    local = args.zip or (find_local_archive() if args.url is None else None)
    try:
        source: Path | str = local if local else (args.url or latest_download_url())
        if not local:
            LOG.info("Using latest official export: %s", source)
        temporary_output = args.output.with_suffix(args.output.suffix + ".part")
        try:
            with open_archive(source) as archive:
                total, counts = write_pipeline(archive, temporary_output, args.limit, args.chunk_size)
            temporary_output.replace(args.output)
        except Exception:
            temporary_output.unlink(missing_ok=True)
            raise
    except (OSError, sqlite3.Error, zipfile.BadZipFile, RuntimeError, urllib.error.URLError, pa.ArrowException, etree.XMLSyntaxError, ValueError) as exc:
        LOG.error("Pipeline failed: %s", exc)
        return 1
    LOG.info("Wrote %s units to %s", f"{total:,}", args.output)
    LOG.info("Rows by technology: %s", dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
