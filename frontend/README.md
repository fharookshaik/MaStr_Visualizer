# Frontend Documentation: High-Performance Visualization

The frontend is a Streamlit-based application that leverages WebGL for high-density spatial visualization and Plotly for interactive analytics.

## 🗺️ The Visualization Layer: PyDeck (Deck.GL)

We chose **PyDeck** over standard libraries like Folium or Matplotlib for a specific reason: **Performance**.

### 1. WebGL Rendering
PyDeck sends coordinates to the GPU. This allows us to render hundreds of thousands of points simultaneously with zero lag. We use the `MVTLayer`, which fetches binary tiles from our backend.

### 2. Visual Hierarchy & "Power-to-Pixel" Scaling
To make the data readable, we implemented dynamic scaling. The radius of a point is not static; it is a function of the unit's capacity:
```python
get_radius="5 + (Bruttoleistung / 200)"
```
This ensures that a massive offshore wind farm is visually dominant over a small rooftop solar array, providing instant geographical insight.

## 📈 Dashboard Logic: Reactive Filters

The frontend uses a **reactive metadata pattern**:
1. Upon selecting a **Unit Type**, the app calls `/api/metadata/{unit_type}`.
2. It dynamically builds sidebar multiselect widgets for columns like `Hersteller` (Wind) or `ArtDerSolaranlage` (Solar).
3. These filters are passed as query parameters to the MVT layer, forcing the map to re-render only the relevant data.

## 📊 Analytics Tab
We use **Plotly Express** for the analytics tab because it handles large DataFrames efficiently and provides out-of-the-box interactivity (zoom, hover, export).
- **Growth Chart:** Line chart of capacity over time.
- **Top Players:** Horizontal bar chart of the top 10 categories.
- **Status Pie:** Breakdown of operational readiness.

## 🧩 Why Streamlit?
Streamlit allowed us to build a complex, two-page analytics application entirely in Python, making it easy to maintain and iterate. By coupling it with **WebGL (PyDeck)**, we overcame Streamlit's typical performance bottlenecks for large datasets.
