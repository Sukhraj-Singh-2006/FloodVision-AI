import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="FloodVision AI", page_icon="🌊", layout="wide")
st.title("🌊 FloodVision AI")
st.caption("Satellite-inspired flood impact dashboard | Educational prototype — not operational data")

st.warning("Demo mode: the map layers and affected assets below are illustrative synthetic examples, not detections from real Sentinel imagery. Do not use for emergency decisions.")

with st.sidebar:
    st.header("Analysis settings")
    area = st.selectbox("Area of interest", ["Trishuli River corridor, Nepal", "Custom area (demo only)"])
    event_date = st.date_input("Flood event date", value=pd.to_datetime("2026-08-26"))
    st.selectbox("Radar input", ["Sentinel-1 (planned integration)", "Upload GeoTIFF (not connected yet)"])
    st.selectbox("Optical input", ["Sentinel-2 (optional / cloud permitting)", "Not used"])
    st.button("Run illustrative analysis", help="This prototype displays example data only.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Illustrative flood area", "2.4 km²", "synthetic demo")
m2.metric("Assets potentially exposed", "18", "synthetic demo")
m3.metric("Road segments flagged", "3", "synthetic demo")
m4.metric("Settlements needing review", "2", "synthetic demo")

# Synthetic example coordinates near the Trishuli corridor; explicitly illustrative.
flood = pd.DataFrame({
    "label": ["Illustrative changed area 1", "Illustrative changed area 2", "Illustrative changed area 3"],
    "lat": [27.90, 27.94, 27.97], "lon": [85.00, 85.04, 85.08],
    "kind": ["Possible flood/debris change"]*3
})
assets = pd.DataFrame({
    "asset": ["Building cluster A", "Road segment B", "Bridge crossing C", "Building cluster D", "Road segment E"],
    "type": ["Buildings", "Road", "Bridge", "Buildings", "Road"],
    "lat": [27.91, 27.93, 27.95, 27.96, 27.98],
    "lon": [85.02, 85.035, 85.05, 85.065, 85.085],
    "status": ["Review", "Potentially exposed", "Review", "Potentially exposed", "Review"]
})
left, right = st.columns([1.5, 1])
with left:
    st.subheader("Impact overview map")
    fig = go.Figure()
    fig.add_trace(go.Scattermap(
        lat=flood.lat, lon=flood.lon, mode="markers",
        marker=dict(size=22, color="orange", opacity=0.65),
        name="Illustrative change zones", text=flood.label, hovertemplate="%{text}<extra></extra>"
    ))
    fig.add_trace(go.Scattermap(
        lat=assets.lat, lon=assets.lon, mode="markers",
        marker=dict(size=11, color="red"), name="Example infrastructure",
        text=assets.asset, hovertemplate="%{text}<extra></extra>"
    ))
    fig.update_layout(map_style="open-street-map", map_center={"lat":27.94,"lon":85.045},
                      map_zoom=10, height=520, margin=dict(l=0,r=0,t=10,b=0),
                      legend=dict(orientation="h", y=1.02))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Locations and overlays are synthetic placeholders for interface demonstration.")
with right:
    st.subheader("Settlement connectivity (example)")
    connectivity = pd.DataFrame({
        "Settlement": ["Village A", "Village B", "Village C", "Village D"],
        "Road access": ["Connected", "Needs review", "Needs review", "Connected"],
        "Nearest service": ["Town clinic", "District hospital", "District hospital", "Town clinic"]
    })
    st.dataframe(connectivity, hide_index=True, use_container_width=True)
    st.subheader("Infrastructure review queue")
    st.dataframe(assets[["asset","type","status"]], hide_index=True, use_container_width=True)

st.subheader("Draft situation report")
st.markdown(f"""
**Area:** {area}  
**Event date selected:** {event_date}  
**Status:** Demonstration only; no satellite data has been processed.  

The prototype interface demonstrates how a flood-response analyst could review candidate change zones,
infrastructure near those zones, and settlements requiring road-connectivity checks. The values and
locations shown here are synthetic examples and must not be treated as verified impact estimates.
""")

with st.expander("Data sources and planned processing"):
    st.markdown("""
- Sentinel-1 SAR: planned input for pre/post-event change analysis.
- Sentinel-2 optical imagery: optional corroboration when cloud conditions allow.
- OpenStreetMap pre-event snapshot: planned infrastructure layer; credit © OpenStreetMap contributors.
- Copernicus DEM: planned terrain/elevation analysis.
- EMSR927 reference maps: evaluation only, never model inputs.
- Required attribution when using actual data: “Contains modified Copernicus Sentinel data 2026.”
- Required DEM attribution: “Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.”
""")
st.caption("Prototype limitations: no real satellite imagery, trained segmentation model, or verified road-network routing is included yet.")
