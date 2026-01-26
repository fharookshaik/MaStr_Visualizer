# MaStr Visualizer

A high-performance, containerized web application for visualizing German energy market data from the **MaStR** (Marktstammdatenregister) database. This project provides interactive mapping and advanced analytics for renewable energy infrastructure across Germany.

## Features

- **High-Performance Vector Tiles**: WebGL-based mapping with Mapbox Vector Tiles for smooth interaction with large datasets
- **Advanced Analytics**: Temporal growth analysis, categorical breakdowns, and operational status tracking
- **Interactive Dashboard**: Streamlit-based frontend with PyDeck for 3D mapping and Plotly for data visualization
- **Containerized Deployment**: Docker-based setup with PostgreSQL, PostGIS, and multi-tier architecture
- **RESTful API**: FastAPI backend with comprehensive endpoints for data access and visualization

## Data Source

**Official Source**: [Marktstammdatenregister (MaStR)](https://www.marktstammdatenregister.de/) - German Federal Network Agency (Bundesnetzagentur)

**Processing Library**: `mastr_lite`,A customized version of [open-mastr](https://github.com/OpenEnergyPlatform/open-mastr) Python package

**Coverage**: Germany-wide renewable energy infrastructure including:
- Wind turbines (onshore & offshore)
- Solar installations (rooftop & ground-mounted)
- Energy storage systems
- Biomass, hydro, combustion, and nuclear facilities

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   FastAPI       │    │   PostgreSQL    │
│   Frontend      │◄──►│   Backend       │◄──►│   + PostGIS     │
│                 │    │                 │    │                 │
│ • PyDeck Maps   │    │ • Vector Tiles  │    │ • Spatial Data  │
│ • Plotly Charts │    │ • Analytics API │    │ • Async Queries │
│ • Interactive   │    │ • REST Endpoints│    │ • GIST Indexes  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                         Auto-population
                     (runs on first startup)
                              │
                              ▼
                    ┌─────────────────┐
                    │   open-mastr    │
                    │   (mastr_lite)  │
                    │                 │
                    │ • XML Downloads │
                    │ • Data Processing│
                    │ • Bulk Loading  │
                    └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 8GB RAM (recommended 16GB for optimal performance)
- 2GB free disk space for data processing

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/fharookshaik/MaStr_Visualizer.git
   cd MaStr_Visualizer
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your preferences if needed
   ```

3. **Start the application:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - Frontend Dashboard: http://localhost:8501
   - API Documentation: http://localhost:8000/docs
   - Alternative API Docs: http://localhost:8000/redoc

**Note**: First startup will automatically download and process ~2700MB of MaStR data, which may take 30-60 minutes depending on your internet connection.

## 📋 API Endpoints

### Vector Tile Service (High Performance)
```bash
GET /api/tiles/{unit_type}/{z}/{x}/{y}
```
- **unit_type**: `wind`, `solar`, `storage`, `biomass`, `hydro`, `combustion`, `nuclear`
- **z**: Zoom level (0-19)
- **x**, **y**: Tile coordinates
- **Response**: Binary MVT data for interactive mapping

### Analytics API
```bash
GET /api/stats/advanced/{unit_type}
```
Returns comprehensive temporal and categorical analytics including:
- Growth trends by year
- Operational status breakdown
- Top categories by capacity

### Metadata API
```bash
GET /api/metadata/{unit_type}
```
Returns filterable column values for dynamic UI controls

### Complete API Reference
See interactive documentation at: http://localhost:8000/docs

## Use Cases

### For Energy Professionals
- **Site Analysis**: Identify optimal locations for new installations
- **Market Research**: Analyze renewable energy trends and capacity growth
- **Competitive Intelligence**: Track installations by manufacturer and technology

### For Researchers
- **Academic Studies**: Access comprehensive German energy infrastructure data
- **Policy Analysis**: Evaluate renewable energy deployment patterns
- **Spatial Analysis**: Leverage GIS capabilities for regional studies

### For Developers
- **Data Integration**: RESTful APIs for custom applications
- **Visualization**: High-performance mapping components
- **Analytics**: Advanced statistical endpoints

## 🔧 Configuration

### Environment Variables

| Variable      | Default     | Description       |
|---------------|-------------|-------------------|
| `DB_HOST`     | `localhost` | PostgreSQL host   |
| `DB_PORT`     | `5432`      | PostgreSQL port   |
| `DB_NAME`     | `mastr_db`  | Database name     |
| `DB_USER`     | `postgres`  | Database user     |
| `DB_PASSWORD` | `1234`      | Database password |
| `DB_SCHEMA`   | `public`    | Database schema   |
| `LOG_LEVEL`   | `INFO`      | Logging level     |

### Docker Configuration

The project uses a three-tier Docker architecture:
- **Tier 1**: PostgreSQL with PostGIS extension
- **Tier 2**: FastAPI backend with automatic data population
- **Tier 3**: Streamlit frontend with interactive dashboard

## Performance Features

### Vector Tile Optimization
- **Spatial Indexing**: GIST indexes on geometry columns for fast queries
- **Binary Encoding**: Direct MVT generation without Python object conversion
- **Async Operations**: Non-blocking database operations for high concurrency
- **Tile Caching**: Ready for Redis or CDN integration

### Database Performance
- **Connection Pooling**: Configurable pool size (5-10 connections)
- **Bulk Operations**: Efficient data loading and processing
- **Spatial Queries**: Optimized coordinate transformations

### Frontend Performance
- **WebGL Rendering**: GPU-accelerated mapping with PyDeck
- **Dynamic Filtering**: Real-time data filtering without page reloads
- **Responsive Design**: Works on desktop and mobile devices

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License and Data Usage

### Data License
The MaStR data is provided by the German Federal Network Agency (Bundesnetzagentur) under German open data policies. This project acknowledges and complies with all data usage requirements.

### Code License
[Specify your project's license here - e.g., MIT License]

### Attribution
This project uses a customized version of the [open-mastr](https://github.com/OpenEnergyPlatform/open-mastr) Python package for data processing. We acknowledge the excellent work of the open-mastr development team.

## 🆘 Support

### Documentation
- [API Documentation](docs/API.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Data Processing](docs/DATA.md)
- [Frontend Guide](docs/FRONTEND.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

### Getting Help
1. Check the [troubleshooting guide](docs/TROUBLESHOOTING.md)
2. Review the [API documentation](docs/API.md)
3. Check existing issues in the project repository
4. Create a new issue with detailed information

## Contact

For questions, suggestions, or collaboration opportunities:
- Create an issue in the repository

## Acknowledgments

- **Bundesnetzagentur**: For providing the official MaStR data
- **open-mastr Team**: For the excellent data processing library
- **FastAPI Community**: For the high-performance web framework
- **Streamlit Team**: For the interactive dashboard framework
- **PostGIS Team**: For spatial database capabilities

---

**Note**: This project is for educational and research purposes. Always verify data accuracy for critical applications.