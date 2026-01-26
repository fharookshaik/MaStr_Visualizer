# Frontend Documentation

This document provides comprehensive information about the MaStr Visualizer frontend application, including its architecture, components, and user interface design.

## Overview

The frontend is built using **Streamlit**, a Python web framework designed for data applications. It provides an interactive dashboard with two main components:

1. **Map Explorer**: Interactive 3D mapping with PyDeck
2. **Analytics Tab**: Data visualization and statistics with Plotly

## Technology Stack

### Core Technologies

- **Streamlit**: Python web framework for data applications
- **PyDeck**: WebGL-based mapping library for high-performance spatial visualization
- **Plotly**: Interactive charting and analytics visualization
- **Requests**: HTTP client for API communication
- **Pandas**: Data manipulation and analysis

### Key Features

- **GPU-Accelerated Mapping**: WebGL rendering for large datasets
- **Real-time Filtering**: Dynamic data filtering without page reloads
- **Responsive Design**: Works on desktop and mobile devices
- **Caching**: Streamlit's built-in caching for performance
- **Interactive Charts**: Hover effects, zoom, and export capabilities

## Application Structure

### Main Application (`frontend/app.py`)

The main application is organized into several key functions:

#### 1. Configuration and Setup

```python
# Page configuration
st.set_page_config(page_title="MaStr Visualizer", layout="wide")

# Environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MAP_BACKEND_URL = os.getenv("MAP_BACKEND_URL", "http://localhost:8000")

# Unit type mapping
UNIT_TYPES = {
    "solar": "Solar", "wind": "Wind", "storage": "Storage",
    "biomass": "Biomass", "hydro": "Hydro", "combustion": "Combustion", "nuclear": "Nuclear"
}
```

#### 2. Data Fetching Functions

```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_metadata(unit_type):
    """Fetch filter metadata for dynamic UI controls."""
    try:
        return requests.get(f"{BACKEND_URL}/api/metadata/{unit_type}").json()
    except: 
        return {}

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_advanced_stats(unit_type):
    """Fetch advanced analytics data."""
    try:
        return requests.get(f"{BACKEND_URL}/api/stats/advanced/{unit_type}").json()
    except: 
        return {}

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_basic_stats(unit_type):
    """Fetch basic statistics data."""
    try:
        return requests.get(f"{BACKEND_URL}/api/stats", params={"unit_type": unit_type}).json()
    except: 
        return []
```

**Caching Strategy**:
- **Metadata**: Cached for 1 hour (rarely changes)
- **Statistics**: Cached for 5 minutes (frequent updates)
- **Advanced Stats**: Cached for 5 minutes (computationally expensive)

#### 3. Sidebar and Controls

```python
def render_sidebar():
    """Render the sidebar with unit selection and filters."""
    st.sidebar.title("MaStr Visualizer")
    unit_type = st.sidebar.selectbox("Unit Type", options=list(UNIT_TYPES.keys()), format_func=lambda x: UNIT_TYPES[x])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")
    
    metadata = get_metadata(unit_type)
    filters = {}
    
    for col, values in metadata.items():
        sel = st.sidebar.multiselect(f"Filter {col}", options=values, key=f"filter_{unit_type}_{col}")
        if sel:
            filters[col] = ",".join(sel)
            
    return unit_type, filters
```

**Dynamic Filter Generation**:
- Automatically generates filter controls based on unit type
- Supports multi-select for categorical filtering
- Real-time filter application to maps and charts

#### 4. Map Visualization

```python
def render_map(unit_type, filters):
    """Render the interactive map with vector tiles."""
    st.subheader(f"🗺️ {UNIT_TYPES[unit_type]} Spatial Distribution")
    
    # Construct Tile URL with filters
    tile_url = f"{MAP_BACKEND_URL}/api/tiles/{unit_type}/{{z}}/{{x}}/{{y}}"
    if filters:
        query_str = "&".join([f"{k}={v}" for k, v in filters.items()])
        tile_url += f"?{query_str}"
        
    # Create PyDeck layer
    mvt_layer = pdk.Layer(
        "MVTLayer",
        data=tile_url,
        get_fill_color="[255, 140, 0, 200]",
        get_line_color=[255, 255, 255, 120],
        point_radius_min_pixels=3,
        point_radius_max_pixels=15,
        get_radius="5 + (Bruttoleistung / 200)",
        pickable=True,
        auto_highlight=True,
        unique_id_property="EinheitMastrNummer",
    )

    # Configure deck
    deck = pdk.Deck(
        layers=[mvt_layer],
        initial_view_state=pdk.ViewState(latitude=51.16, longitude=10.45, zoom=5, min_zoom=4, max_zoom=14),
        tooltip={"html": "<b>{Name}</b><br>ID: {EinheitMastrNummer}<br>Power: {Bruttoleistung} kW<br>Status: {EinheitBetriebsstatus}"},
        map_style="dark"
    )
    st.pydeck_chart(deck, width='stretch')
```

**Map Features**:
- **Vector Tiles**: High-performance MVT rendering
- **Dynamic Filtering**: Real-time filter application
- **Power-to-Pixel Scaling**: Visual hierarchy based on capacity
- **Interactive Tooltips**: Detailed information on hover
- **Dark Map Style**: Optimized for energy data visualization

#### 5. Analytics Dashboard

```python
def render_dashboard(unit_type, filters):
    """Render the analytics dashboard with charts."""
    st.subheader(f"📊 {UNIT_TYPES[unit_type]} Insights")
    
    # Basic statistics
    basic_data = get_basic_stats(unit_type)
    if basic_data:
        df_basic = pd.DataFrame(basic_data)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Units", f"{df_basic['count'].sum():,.0f}")
        col2.metric("Total Capacity", f"{df_basic['total_capacity'].sum()/1e6:.2f} GW")
        col3.metric("States Active", len(df_basic))

    # Advanced analytics
    adv = get_advanced_stats(unit_type)
    if not adv:
        st.error("Could not load advanced statistics.")
        return

    # Layout with columns
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("**Capacity Growth over Time**")
        df_temp = pd.DataFrame(adv["temporal"])
        if not df_temp.empty:
            fig = px.line(df_temp, x="year", y="capacity", labels={"capacity": "Capacity (kW)"}, template="plotly_dark")
            fig.update_traces(line_color='#FF8C00')
            st.plotly_chart(fig, width='stretch')

    with c2:
        st.markdown(f"**Top 10 by {adv['categories']['column']}**")
        df_cat = pd.DataFrame(adv["categories"]["data"])
        if not df_cat.empty:
            fig = px.bar(df_cat, x="capacity", y="category", orientation='h', template="plotly_dark")
            fig.update_traces(marker_color='#4B0082')
            st.plotly_chart(fig, width='stretch')

    # Additional charts
    c3, c4 = st.columns([1, 2])
    with c3:
        st.markdown("**Operational Status**")
        df_status = pd.DataFrame(adv["status"])
        if not df_status.empty:
            fig = px.pie(df_status, values="count", names="status", hole=.4, template="plotly_dark")
            st.plotly_chart(fig, width='stretch')
    
    with c4:
        st.markdown("**Regional Capacity (kW)**")
        if basic_data:
            st.bar_chart(df_basic.set_index("Bundesland")["total_capacity"])
```

**Analytics Features**:
- **Growth Charts**: Temporal capacity trends
- **Categorical Analysis**: Top categories by capacity
- **Status Breakdown**: Operational status distribution
- **Regional Analysis**: Bundesland-level statistics
- **Interactive Charts**: Zoom, hover, and export capabilities

## User Interface Design

### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│                    Sidebar (Filters)                    │
├─────────────────────────────────────────────────────────┤
│                    Main Content Area                    │
│  ┌─────────────────┐  ┌───────────────────────────────┐ │
│  │   Map Explorer  │  │        Analytics Tab          │ │
│  │                 │  │                               │ │
│  │   PyDeck Map    │  │  ┌─────────────┐ ┌──────────┐ │ │
│  │                 │  │  │ Growth Chart│ │ Top 10   │ │ │
│  │ Interactive     │  │  │             │ │ by Type  │ │ │
│  │                 │  │  └─────────────┘ └──────────┘ │ │
│  │ Vector Tiles    │  │  ┌─────────────┐ ┌──────────┐ │ │
│  │                 │  │  │ Status Pie  │ │ Regional │ │ │
│  │                 │  │  │             │ │ Capacity │ │ │
│  └─────────────────┘  │  └─────────────┘ └──────────┘ │ │
│                     Tabs (Map Explorer | Analytics)   │ │
└─────────────────────────────────────────────────────────┘
```

### Color Scheme

- **Primary Color**: Orange (`#FF8C00`) - Energy theme
- **Secondary Color**: Indigo (`#4B0082`) - Professional appearance
- **Background**: Dark theme for better data visualization
- **Map Style**: Dark map style for contrast with energy data

### Typography and Styling

- **Font**: Streamlit default with custom styling
- **Headers**: Clear hierarchy with emojis for visual cues
- **Metrics**: Large, prominent display for key statistics
- **Charts**: Dark theme with custom color schemes

## Performance Optimization

### 1. Caching Strategy

```python
# Strategic caching for different data types
@st.cache_data(ttl=3600)  # 1 hour - metadata (rarely changes)
@st.cache_data(ttl=300)   # 5 minutes - statistics (frequent updates)
@st.cache_data(ttl=60)    # 1 minute - real-time data
```

**Cache Management**:
- **TTL Configuration**: Appropriate cache durations for different data types
- **Cache Invalidation**: Automatic cache clearing on data updates
- **Memory Management**: Efficient cache size management

### 2. Data Processing

```python
# Efficient data processing
df_basic = pd.DataFrame(basic_data)
df_temp = pd.DataFrame(adv["temporal"])
df_cat = pd.DataFrame(adv["categories"]["data"])
```

**Optimization Techniques**:
- **DataFrame Creation**: Efficient pandas operations
- **Memory Usage**: Minimize data copying
- **Processing Time**: Fast data transformation

### 3. Visualization Performance

#### PyDeck Optimization
```python
# Efficient vector tile rendering
mvt_layer = pdk.Layer(
    "MVTLayer",
    data=tile_url,
    get_fill_color="[255, 140, 0, 200]",  # GPU-accelerated colors
    get_radius="5 + (Bruttoleistung / 200)",  # Dynamic sizing
    pickable=True,  # Enable interactions
    auto_highlight=True,  # Visual feedback
)
```

#### Plotly Optimization
```python
# Optimized chart rendering
fig = px.line(df_temp, x="year", y="capacity", template="plotly_dark")
fig.update_traces(line_color='#FF8C00')  # Custom styling
st.plotly_chart(fig, width='stretch')  # Responsive sizing
```

## Interactivity Features

### 1. Dynamic Filtering

```python
# Real-time filter application
if filters:
    query_str = "&".join([f"{k}={v}" for k, v in filters.items()])
    tile_url += f"?{query_str}"
```

**Filter Types**:
- **Categorical**: Multi-select for categories like manufacturer
- **Geographic**: Bundesland selection
- **Status**: Operational status filtering
- **Combined**: Multiple filters applied simultaneously

### 2. Map Interactions

- **Zoom and Pan**: Standard map navigation
- **Tooltips**: Hover information display
- **Click Events**: Detailed unit information
- **Filter Feedback**: Visual indication of applied filters

### 3. Chart Interactions

- **Hover Effects**: Data point information
- **Zoom and Pan**: Chart navigation
- **Legend Interactions**: Toggle data series
- **Export Options**: Download chart images

## Responsive Design

### Mobile Optimization

```python
# Responsive chart sizing
st.plotly_chart(fig, width='stretch')  # Full width charts
st.pydeck_chart(deck, width='stretch')  # Full width maps
```

**Mobile Features**:
- **Touch Interactions**: Optimized for touch devices
- **Responsive Layout**: Adapts to screen size
- **Simplified Controls**: Streamlined mobile interface

### Desktop Features

- **Multi-column Layout**: Efficient use of screen space
- **Advanced Controls**: Full filtering capabilities
- **High-resolution Charts**: Crisp visualization

## Error Handling

### Graceful Degradation

```python
# Error handling for API failures
try:
    return requests.get(f"{BACKEND_URL}/api/metadata/{unit_type}").json()
except: 
    return {}
```

**Error Scenarios**:
- **API Failures**: Graceful handling of backend issues
- **Data Issues**: Empty data handling
- **Network Problems**: Connection error management

### User Feedback

- **Loading States**: Clear indication of data loading
- **Error Messages**: Informative error display
- **Retry Mechanisms**: Automatic retry for transient failures

## Development and Customization

### Adding New Unit Types

1. **Update UNIT_TYPES mapping**:
```python
UNIT_TYPES = {
    # ... existing types
    "new_type": "New Type Display Name"
}
```

2. **Backend Support**: Ensure backend API supports the new type
3. **Frontend Testing**: Test filtering and visualization

### Customizing Visualizations

#### Map Styling
```python
# Custom map layer styling
mvt_layer = pdk.Layer(
    "MVTLayer",
    data=tile_url,
    get_fill_color="[255, 140, 0, 200]",  # Custom colors
    get_radius="5 + (Bruttoleistung / 200)",  # Custom sizing
    # Add more custom properties
)
```

#### Chart Styling
```python
# Custom chart themes
fig = px.line(df_temp, x="year", y="capacity", template="plotly_dark")
fig.update_traces(line_color='#FF8C00', line_width=3)  # Custom styling
fig.update_layout(title_font_size=20, font_size=12)  # Layout customization
```

### Performance Monitoring

#### Streamlit Metrics
```python
# Monitor performance
import time
start_time = time.time()
# Data processing code
processing_time = time.time() - start_time
st.write(f"Processing time: {processing_time:.2f} seconds")
```

#### Browser Developer Tools
- **Network Tab**: Monitor API calls and data transfer
- **Performance Tab**: Analyze rendering performance
- **Console**: Check for JavaScript errors

## Integration with Backend

### API Communication

```python
# Consistent API communication pattern
response = requests.get(f"{BACKEND_URL}/api/stats", params={"unit_type": unit_type})
data = response.json()
```

**API Endpoints Used**:
- `/api/metadata/{unit_type}` - Filter options
- `/api/stats/advanced/{unit_type}` - Analytics data
- `/api/stats` - Basic statistics
- `/api/tiles/{unit_type}/{z}/{x}/{y}` - Vector tiles

### Data Flow

```
Frontend Request → Backend API → Database Query → Response → Frontend Display
      ↓                ↓              ↓            ↓              ↓
   User Action → FastAPI Endpoint → PostgreSQL → JSON Data → Streamlit UI
```

This frontend documentation provides comprehensive guidance for understanding, maintaining, and extending the MaStr Visualizer user interface.