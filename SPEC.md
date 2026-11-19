# SPEC.md: MaStr_Visualizer

## 1. Project Overview
**Goal**: Build a bilingual (DE/EN), high-performance web application to visualize and analyze the German Marktstammdatenregister (MaStR).  
**Constraints**: 
- **Zero backend / Zero database costs**. 100% static hosting (GitHub Pages).
- **Weekly automated refresh** via GitHub Actions.
- **MIT License** for all custom code. (Data remains under `dl-de/by-2.0` with proper attribution).
- **No `open-mastr`**: It is AGPL and too slow. Use the custom streaming pipeline defined below.
- **Target Hardware**: Local dev on MacOS M4, 16GB RAM. CI on GitHub Actions `ubuntu-latest` (4 vCPU, 16GB RAM).
- **Tooling**: Use **`uv`** for all Python environment and dependency management.

## 2. Architecture: "Compile the Database Away"
All heavy lifting happens in CI (or locally during dev). The browser only downloads highly optimized, static artifacts and queries them client-side.
1. **Ingestion**: GitHub Actions downloads the daily `Gesamtdatenexport_*.zip` (~3.2 GB).
2. **Streaming Parse**: A custom Python script streams the XML directly from the ZIP (no full extraction) using `lxml.etree.iterparse`, writing chunks directly to **Parquet** via `pyarrow`. (Expected time: < 3 mins on M4 / GitHub Actions with `uv`).
3. **Aggregation**: DuckDB (CLI) reads the Parquet to generate tiny JSON summaries (weekly deltas, regional KPIs, top operators).
4. **Vector Tiles**: `tippecanoe` converts the Parquet (exported to CSV) into a single `.pmtiles` file for the map.
5. **Frontend**: Vite + React + TypeScript + Tailwind CSS. 
   - **Map**: MapLibre GL JS + OpenFreeMap (basemap, no API key) + `pmtiles` protocol.
   - **Analytics/Table**: `duckdb-wasm` runs SQL directly against the hosted `units.parquet` via HTTP Range Requests, enabling dynamic filtering without a backend.

## 3. Data Pipeline Specification (Custom, MIT)
**DO NOT** use `open-mastr`. Implement this exact pipeline in `scripts/pipeline.py`.

### 3.1. Streaming XML to Parquet (`scripts/pipeline.py`)
- Download the latest ZIP from: `https://download.marktstammdatenregister.de/Gesamtdatenexport_YYYYMMDD_XX.X.zip`
- Use `zipfile` and `lxml.etree.iterparse` to stream-parse `Einheiten.xml` (or the equivalent core unit file in the v26.x schema).
- **Target Parquet Schema (`units.parquet`)**:
  - `mastr_id` (String, Primary Key)
  - `tech_type` (String: e.g., 'Solar', 'Wind', 'Biomass', 'Hydro', 'Storage')
  - `capacity_mw` (Float32)
  - `status` (String: 'In Betrieb', 'Geplant', 'Stillgelegt')
  - `lat` (Float32, nullable)
  - `lon` (Float32, nullable)
  - `municipality_key` (String, nullable)
  - `municipality_name` (String, nullable)
  - `county` (String, nullable)
  - `state` (String, nullable)
  - `commissioning_date` (Date32, nullable)
  - `operator_name` (String, nullable)
- Write to Parquet in 100,000-row chunks using `pyarrow` to keep RAM usage < 2GB.

### 3.2. Aggregation (`scripts/aggregate.sql`)
Run via DuckDB CLI: `duckdb -c ".read scripts/aggregate.sql"`
Generate `public/data/summary.json` containing:
- `total_capacity_mw` by `tech_type` and `status`.
- `weekly_delta`: Compare current week's totals to a stored `history.json` (append-only, tiny file committed to Git).
- `top_municipalities`: Top 20 by capacity density (MW per km² or per capita, using static area/population lookup tables committed to repo).
- `data_quality`: Percentage of units with valid `lat`/`lon` vs. municipality-level only.

### 3.3. Map Tile Generation (`scripts/build_tiles.sh`)
1. Export filtered units to CSV: `duckdb -c "COPY (SELECT mastr_id, tech_type, capacity_mw, status, lat, lon, municipality_name FROM 'units.parquet' WHERE lat IS NOT NULL AND lon IS NOT NULL) TO 'temp_units.csv' (HEADER, DELIMITER ',');"`
2. Run Tippecanoe: 
   ```bash
   tippecanoe --output=public/data/map.pmtiles --force \
     --layer=units \
     --drop-densest-as-needed \
     --extend-zooms-if-still-dropping \
     --maximum-zoom=14 \
     --csv=temp_units.csv
   ```

## 4. Frontend Stack & UX
- **Framework**: Vite + React + TypeScript.
- **Styling**: Tailwind CSS + `lucide-react` for icons.
- **i18n**: `react-i18next` with `de.json` and `en.json`.
- **Map**: 
  - `maplibre-gl`
  - `pmtiles` (to register the `pmtiles://` protocol)
  - **Basemap**: OpenFreeMap (`https://tiles.openfreemap.org/styles/liberty`) – free, no key, no limits.
- **Analytics Engine**: `@duckdb/duckdb-wasm`. Initialize on mount, register `https://<your-repo>.github.io/data/units.parquet` via `DuckDBDataProtocol.HTTP`.

### 4.1. UX Features (Inspired by, not copying, goal100)
1. **Split View**: Map on the right (60%), interactive data table/filters on the left (40%).
2. **Hexbin Aggregation**: The `.pmtiles` will naturally aggregate points at low zoom. At zoom > 10, individual points appear.
3. **Deep Linking**: URL state sync. Filtering by "Solar" in "Bayern" updates URL to `?tech=Solar&state=Bayern`.
4. **Region Search**: Autocomplete dropdown for Bundesland, Landkreis, Gemeinde. Selecting one draws a boundary outline (use a small static GeoJSON of German municipalities, ~10MB, or fetch from a free WFS only when searched).
5. **Detail Card**: Clicking a map point or table row opens a slide-over panel with unit details, pulling from the DuckDB query result.

## 5. Milestones for Claude Code Agent
Execute these milestones sequentially. Do not proceed to the next until the current one is verified.

### M0: Project Scaffolding
- [ ] Initialize Vite React TS project.
- [ ] Install dependencies: `tailwindcss`, `maplibre-gl`, `pmtiles`, `duckdb-wasm`, `react-i18next`, `lucide-react`.
- [ ] Set up basic routing and i18n boilerplate (DE/EN toggle).
- [ ] Initialize Python data pipeline directory with `uv`: `uv venv`, `uv pip install lxml pyarrow requests`.

### M1: Local Data Pipeline (The "No open-mastr" Rule)
- [ ] Create `scripts/pipeline.py`. Implement `lxml` + `pyarrow` streaming parser. 
- [ ] *Test locally on M4*: Download a sample MaStR ZIP, run the script via `uv run scripts/pipeline.py`, verify `units.parquet` is generated in < 3 minutes and RAM stays under 4GB.
- [ ] Create `scripts/aggregate.sql` and `scripts/build_tiles.sh`.
- [ ] Verify `public/data/summary.json` and `public/data/map.pmtiles` are generated correctly.

### M2: Core Frontend & Map Integration
- [ ] Implement MapLibre GL component with OpenFreeMap basemap.
- [ ] Register PMTiles protocol and load `map.pmtiles`.
- [ ] Implement the left-sidebar filter panel (Tech, Status, State).
- [ ] Connect filter state to MapLibre `setFilter` and DuckDB-WASM queries.

### M3: Advanced Analytics & Polish
- [ ] Implement DuckDB-WASM data table below the filters (paginated, sortable).
- [ ] Build the "Advanced Analysis" dashboard view: 
  1. Weekly Delta chart (using `summary.json`).
  2. Tech Mix pie chart.
  3. Data Quality indicator (% with exact coordinates).
- [ ] Implement URL state sync (`useSearchParams`).
- [ ] Add proper `dl-de/by-2.0` attribution footer linking to Bundesnetzagentur.

### M4: CI/CD Automation
- [ ] Create `.github/workflows/update-data.yml` using `astral-sh/setup-uv`.
- [ ] Configure cron schedule: `cron: '0 6 * * 1'` (Mondays at 06:00 UTC).
- [ ] Add steps: checkout, setup `uv`, run pipeline, commit & push `public/data/` and `history.json` back to the repo.

## 6. Local Development Setup (MacOS M4, 16GB)
Provide these exact commands to the user to get started:
```bash
# 1. Install system dependencies (Homebrew)
brew install uv duckdb tippecanoe

# 2. Initialize Frontend
npm create vite@latest mastr-visualizer -- --template react-ts
cd mastr-visualizer
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
# (Add tailwind directives to index.css and content paths to tailwind.config.js)
npm install maplibre-gl pmtiles @duckdb/duckdb-wasm react-i18next i18next lucide-react

# 3. Setup Python Data Pipeline Environment
cd .. # back to repo root
uv venv
source .venv/bin/activate
uv pip install lxml pyarrow requests

# 4. Run the pipeline locally (uv run handles the venv activation automatically if preferred)
uv run scripts/pipeline.py
```

## 7. GitHub Actions Workflow Template (`.github/workflows/update-data.yml`)
```yaml
name: Weekly MaStR Data Refresh
on:
  schedule:
    - cron: '0 6 * * 1' # Monday 06:00 UTC
  workflow_dispatch: # Allow manual trigger

permissions:
  contents: write

jobs:
  build-data:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup uv
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
          python-version: '3.12'
          
      - name: Install Python Dependencies
        run: uv pip install --system lxml pyarrow requests
        
      - name: Install DuckDB & Tippecanoe
        run: |
          sudo apt-get update
          sudo apt-get install -y duckdb tippecanoe
          
      - name: Run Custom Pipeline
        run: |
          uv run scripts/pipeline.py
          duckdb -c ".read scripts/aggregate.sql"
          bash scripts/build_tiles.sh
          
      - name: Commit and Push Data
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add public/data/ history.json
          git diff --staged --quiet || git commit -m "chore: weekly MaStR data refresh [skip ci]"
          git push
```

## 8. Critical Constraints & Guardrails for the Agent
1. **Memory Management**: The Python script *must* use `lxml.etree.iterparse`. Do not use `xmltodict` or `pandas.read_xml` on the 3.2GB file; it will OOM on GitHub Actions.
2. **File Size Limits**: GitHub Pages has a 1 GB soft limit. The generated `units.parquet` must be monitored. If it exceeds 500MB, the agent must implement column pruning (e.g., drop verbose text fields, keep only IDs and metrics for the frontend).
3. **CORS**: All data files (`units.parquet`, `map.pmtiles`, `summary.json`) must be served from the same origin (`*.github.io`) to avoid GitHub Pages CORS limitations with HTTP Range Requests.
4. **License**: Ensure no AGPL code (like `open-mastr`) is imported. All custom scripts must have an MIT license header.
5. **`uv` Usage**: The agent must strictly use `uv` commands (`uv venv`, `uv pip install`, `uv run`) for all Python-related setup and execution, avoiding legacy `venv`/`pip` commands.
