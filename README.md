# MaStR Visualizer

A bilingual, static-first application for exploring Germany’s energy installations from the Marktstammdatenregister (MaStR). Browse a high-performance map, filter records, and inspect energy-market trends and data quality.

## Features

- **Interactive map:** MapLibre and PMTiles for exploring German generation assets.
- **Client-side data exploration:** DuckDB-WASM queries Parquet data in the browser.
- **Analytics and data quality:** Summary metrics and analysis views built from the published dataset.
- **German and English UI:** Switch languages from the application header.
- **Reproducible data pipeline:** Stream the official MaStR export into Parquet with Python and `uv`.

## Requirements

- Node.js 20.19+ or 22.12+ and npm
- Python 3.12+ and [`uv`](https://docs.astral.sh/uv/)
- For rebuilding vector tiles: DuckDB, Tippecanoe and the PMTiles CLI

## Run the application

```bash
npm ci
npm run dev
```

Open the local URL printed by Vite. Create a production build with `npm run build`, and preview it with `npm run preview`.

## Data pipeline

The checked-in `public/data/` directory contains the generated map, Parquet data and summaries used by the app. Regenerate the Parquet dataset from the latest official export with:

```bash
uv sync
uv run scripts/pipeline.py
```

You can also provide a previously downloaded MaStR ZIP:

```bash
uv run scripts/pipeline.py --zip /path/to/Gesamtdatenexport.zip
```

After regenerating the Parquet data, rebuild the map artifacts and summary using the project’s documented aggregation and tile-generation scripts. Local raw source archives under `data/raw/` are intentionally ignored by Git.

**Large-file note:** `public/data/units.parquet` and `public/data/map.pmtiles` are tracked with Git LFS. A checkout requires Git LFS to download their contents. The default 100 MB GitHub file limit does not apply to the LFS pointer, but use of Git LFS storage and bandwidth may depend on the repository’s quota and plan.

## Project structure

- `src/` — React, TypeScript, styles and localization
- `public/data/` — generated data served by the frontend
- `scripts/` — data aggregation, conversion and tile-building tools
- `SPEC.md` — project architecture and pipeline specification

## License and data attribution

The repository’s code is licensed under [GNU AGPL-3.0](LICENSE.md). MaStR source data is provided by Germany’s Federal Network Agency (Bundesnetzagentur); follow the applicable data-licensing terms and attribution requirements when redistributing it.
