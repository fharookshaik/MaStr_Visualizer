import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
import plotly.express as px
import os

# Page configuration
st.set_page_config(page_title="MaStr Visualizer", layout="wide")
# st.set_page_config(page_title="MaStr Visualizer", page_icon="⚡", layout="wide")

# Internal URL for server-to-server communication (within Docker network)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
# External URL for browser-to-server communication (from user's machine)
MAP_BACKEND_URL = os.getenv("MAP_BACKEND_URL", "http://localhost:8000")

UNIT_TYPES = {
    "solar": "Solar", "wind": "Wind", "storage": "Storage",
    "biomass": "Biomass", "hydro": "Hydro", "combustion": "Combustion", "nuclear": "Nuclear"
}

# --- Data Fetching ---

@st.cache_data(ttl=3600)
def get_metadata(unit_type):
    try:
        return requests.get(f"{BACKEND_URL}/api/metadata/{unit_type}").json()
    except: return {}

@st.cache_data(ttl=300)
def get_advanced_stats(unit_type):
    try:
        return requests.get(f"{BACKEND_URL}/api/stats/advanced/{unit_type}").json()
    except: return {}

@st.cache_data(ttl=300)
def get_basic_stats(unit_type):
    try:
        return requests.get(f"{BACKEND_URL}/api/stats", params={"unit_type": unit_type}).json()
    except: return []

# --- UI Components ---

def render_sidebar():
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

def render_map(unit_type, filters):
    st.subheader(f"🗺️ {UNIT_TYPES[unit_type]} Spatial Distribution")
    
    # Construct Tile URL with filters using the browser-accessible URL
    tile_url = f"{MAP_BACKEND_URL}/api/tiles/{unit_type}/{{z}}/{{x}}/{{y}}"
    if filters:
        query_str = "&".join([f"{k}={v}" for k, v in filters.items()])
        tile_url += f"?{query_str}"
        
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

    deck = pdk.Deck(
        layers=[mvt_layer],
        initial_view_state=pdk.ViewState(latitude=51.16, longitude=10.45, zoom=5, min_zoom=4, max_zoom=14),
        tooltip={"html": "<b>{Name}</b><br>ID: {EinheitMastrNummer}<br>Power: {Bruttoleistung} kW<br>Status: {EinheitBetriebsstatus}"},
        map_style="dark"
    )
    st.pydeck_chart(deck, width='stretch')

def render_dashboard(unit_type, filters):
    st.subheader(f"📊 {UNIT_TYPES[unit_type]} Insights")
    
    # 1. Basic Stats
    basic_data = get_basic_stats(unit_type)
    if basic_data:
        df_basic = pd.DataFrame(basic_data)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Units", f"{df_basic['count'].sum():,.0f}")
        col2.metric("Total Capacity", f"{df_basic['total_capacity'].sum()/1e6:.2f} GW")
        col3.metric("States Active", len(df_basic))

    # 2. Advanced Stats
    adv = get_advanced_stats(unit_type)
    if not adv:
        st.error("Could not load advanced statistics.")
        return

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

def main():
    unit_type, filters = render_sidebar()
    tab1, tab2 = st.tabs(["🗺️ Map Explorer", "📈 Unit Analytics"])
    
    with tab1: render_map(unit_type, filters)
    with tab2: render_dashboard(unit_type, filters)

if __name__ == "__main__":
    main()
