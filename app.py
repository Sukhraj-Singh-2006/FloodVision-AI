
import math
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import rasterio
import streamlit as st
import planetary_computer
from pystac_client import Client
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject

st.set_page_config(page_title="FloodVision AI | Sentinel-1", page_icon="🌊", layout="wide")
st.title("🌊 FloodVision AI")
st.caption("Historical Sentinel-1 SAR change screening · Punjab, India · research prototype")
st.warning(
    "This is a preliminary satellite change-screening tool, not a validated flood map. "
    "Low radar backscatter can also be caused by smooth surfaces, terrain, agriculture, or acquisition differences. "
    "Do not use for emergency response or rescue decisions."
)

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "sentinel-1-rtc"

# Small AOI around the Sutlej/Rupnagar area. Change these bounds in the sidebar if needed.
PRESET_BBOXES = {
    "Rupnagar / Sutlej corridor, Punjab": [76.35, 30.85, 76.65, 31.15],
    "Sultanpur Lodhi / Beas-Sutlej region, Punjab": [75.05, 31.05, 75.35, 31.35],
}

@st.cache_data(ttl=3600, show_spinner=False)
def search_items(bbox, start, end):
    catalog = Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    search = catalog.search(
        collections=[COLLECTION],
        bbox=bbox,
        datetime=f"{start}T00:00:00Z/{end}T23:59:59Z",
        max_items=40,
    )
    items = list(search.items())
    # Only keep items with a VV asset, and prefer a reasonably large footprint.
    items = [i for i in items if "vv" in i.assets]
    return items


def item_date(item):
    dt = item.properties.get("datetime")
    return pd.to_datetime(dt, utc=True) if dt else pd.Timestamp("1970-01-01", tz="UTC")


def choose_pair(pre_items, post_items):
    if not pre_items or not post_items:
        return None, None, "No Sentinel-1 RTC scenes were found in one of the selected periods. Try widening the dates or changing the AOI."
    # Prefer the same relative orbit, which improves comparability between acquisitions.
    def orbit(i):
        return i.properties.get("sat:relative_orbit")
    pairs = []
    for a in pre_items:
        for b in post_items:
            same_orbit = orbit(a) is not None and orbit(a) == orbit(b)
            same_state = a.properties.get("sat:orbit_state") == b.properties.get("sat:orbit_state")
            # Prefer same orbit, then the closest acquisitions to the middle of their windows.
            score = (0 if same_orbit else 1000) + (0 if same_state else 100) + abs((item_date(b) - item_date(a)).days) * 0.001
            pairs.append((score, a, b, same_orbit))
    pairs.sort(key=lambda x: x[0])
    _, pre, post, same_orbit = pairs[0]
    note = "Same relative orbit selected." if same_orbit else "Warning: no matching relative orbit was found; acquisition geometry may differ."
    return pre, post, note


def read_vv_on_grid(item, bbox, width=600, height=600):
    """Read a Sentinel-1 RTC VV COG into a common geographic grid."""
    asset_key = "vv" if "vv" in item.assets else None
    if asset_key is None:
        raise RuntimeError(f"VV asset not available in item {item.id}")
    href = item.assets[asset_key].href
    west, south, east, north = bbox
    dst_transform = from_origin(west, north, (east - west) / width, (north - south) / height)
    dst = np.full((height, width), np.nan, dtype=np.float32)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff"):
        with rasterio.open(href) as src:
            reproject(
                source=rasterio.band(src, 1),
                destination=dst,
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=src.nodata,
                dst_transform=dst_transform,
                dst_crs="EPSG:4326",
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )
            scale = src.scales[0] if src.scales else 1.0
            offset = src.offsets[0] if src.offsets else 0.0
            if scale != 1.0 or offset != 0.0:
                dst = dst * scale + offset
    valid = np.isfinite(dst)
    if valid.sum() == 0:
        raise RuntimeError("The selected scene does not cover the chosen area. Try a nearby AOI or different dates.")
    # RTC data is normally linear backscatter. Convert to dB if values look like linear power.
    med = float(np.nanmedian(dst))
    if 0 < med < 2:
        dst = 10.0 * np.log10(np.clip(dst, 1e-8, None))
    return dst


def scene_label(item):
    return f"{item.id} · {item_date(item).strftime('%Y-%m-%d')}"

with st.sidebar:
    st.header("Real satellite analysis")
    preset = st.selectbox("Study area", list(PRESET_BBOXES.keys()))
    bbox = PRESET_BBOXES[preset]
    st.caption(f"Bounding box: {bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f} (lon/lat)")
    st.subheader("Historical event windows")
    pre_start = st.date_input("Pre-event start", value=date(2023, 6, 15), key="pre_start")
    pre_end = st.date_input("Pre-event end", value=date(2023, 7, 5), key="pre_end")
    post_start = st.date_input("Post-event start", value=date(2023, 7, 8), key="post_start")
    post_end = st.date_input("Post-event end", value=date(2023, 7, 25), key="post_end")
    threshold = st.slider("Candidate water threshold (VV dB)", min_value=-24, max_value=-8, value=-16, step=1)
    min_change = st.slider("Minimum backscatter drop (dB)", min_value=1, max_value=12, value=3, step=1)
    run = st.button("Fetch Sentinel-1 & analyse", type="primary", use_container_width=True)
    st.caption("Uses public Sentinel-1 RTC data indexed by Microsoft Planetary Computer; internet required.")

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if run:
    if pre_start > pre_end or post_start > post_end:
        st.error("Each start date must be on or before its end date.")
        st.stop()
    with st.spinner("Searching the public Sentinel-1 archive…"):
        try:
            pre_items = search_items(bbox, pre_start.isoformat(), pre_end.isoformat())
            post_items = search_items(bbox, post_start.isoformat(), post_end.isoformat())
            pre_item, post_item, orbit_note = choose_pair(pre_items, post_items)
            if pre_item is None or post_item is None:
                st.session_state.analysis_result = {"error": orbit_note, "pre_count": len(pre_items), "post_count": len(post_items)}
            else:
                with st.spinner("Reading satellite radar backscatter and comparing the two periods…"):
                    pre = read_vv_on_grid(pre_item, bbox)
                    post = read_vv_on_grid(post_item, bbox)
                    valid = np.isfinite(pre) & np.isfinite(post)
                    drop = pre - post  # positive means backscatter became lower after the event
                    # Preliminary candidate mask only. This is not a trained segmentation model.
                    candidates = valid & (post < threshold) & (drop >= min_change)
                    # A 600x600 grid covers the bbox; use approximate local km-per-degree.
                    west, south, east, north = bbox
                    lat_mid = (south + north) / 2
                    pixel_km2 = ((east - west) * 111.32 / pre.shape[1]) * ((north - south) * 111.32 * math.cos(math.radians(lat_mid)) / pre.shape[0])
                    area_km2 = float(candidates.sum() * pixel_km2)
                    st.session_state.analysis_result = {
                        "pre": pre, "post": post, "drop": drop, "valid": valid,
                        "candidates": candidates, "area_km2": area_km2,
                        "pre_item": pre_item, "post_item": post_item,
                        "orbit_note": orbit_note, "bbox": bbox, "threshold": threshold,
                        "min_change": min_change, "pre_count": len(pre_items), "post_count": len(post_items),
                    }
        except Exception as exc:
            st.session_state.analysis_result = {"error": f"{type(exc).__name__}: {exc}", "pre_count": 0, "post_count": 0}

result = st.session_state.analysis_result
if result is None:
    st.info("Choose a study area and click **Fetch Sentinel-1 & analyse**. This version queries real satellite scenes instead of displaying invented flood statistics.")
    st.markdown("**Suggested historical window:** Punjab monsoon flooding, July 2023. Actual usable acquisition dates depend on satellite coverage in the selected area.")
    st.markdown("Data source: [Microsoft Planetary Computer Sentinel-1 RTC](https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc).")
elif "error" in result:
    st.error(result["error"])
    st.write(f"Scenes found: {result.get('pre_count', 0)} pre-event; {result.get('post_count', 0)} post-event.")
    st.write("Try broader date windows (e.g. pre-event June 1–July 7; post-event July 8–August 15) or the other Punjab AOI. The archive may not contain matching coverage for every date/area.")
else:
    pre_item, post_item = result["pre_item"], result["post_item"]
    st.success("Real Sentinel-1 RTC scenes loaded successfully. The highlighted pixels are algorithmic candidates for review, not confirmed flood extent.")
    st.caption(result["orbit_note"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pre-event scene", item_date(pre_item).strftime("%Y-%m-%d"))
    c2.metric("Post-event scene", item_date(post_item).strftime("%Y-%m-%d"))
    c3.metric("Candidate area", f"{result['area_km2']:.2f} km²")
    c4.metric("Candidate pixels", f"{int(result['candidates'].sum()):,}")
    st.caption("Candidate area is a rough pixel-area estimate from the chosen grid. It is not a verified inundation measurement.")

    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
    panels = [(result["pre"], "Pre-event VV backscatter (dB)", "gray", -25, 0),
              (result["post"], "Post-event VV backscatter (dB)", "gray", -25, 0),
              (result["candidates"].astype(float), "Candidate new-water pixels", "Blues", 0, 1)]
    for ax, (arr, title, cmap, vmin, vmax) in zip(axs, panels):
        ax.imshow(arr, cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title, fontsize=10)
        ax.set_axis_off()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    # Plot candidate pixels on a geographic basemap, capped for browser performance.
    candidates = result["candidates"]
    ys, xs = np.where(candidates)
    if len(xs) > 3000:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(xs), 3000, replace=False)
        ys, xs = ys[idx], xs[idx]
    west, south, east, north = result["bbox"]
    height, width = candidates.shape
    lons = west + (xs + 0.5) * (east - west) / width
    lats = north - (ys + 0.5) * (north - south) / height
    map_fig = go.Figure()
    if len(xs):
        map_fig.add_trace(go.Scattermap(
            lat=lats, lon=lons, mode="markers",
            marker=dict(size=5, color="#16a6ff", opacity=0.7),
            name="Candidate pixels", hovertemplate="Candidate pixel<extra></extra>"
        ))
    map_fig.update_layout(
        map_style="open-street-map", map_center={"lat": (south+north)/2, "lon": (west+east)/2},
        map_zoom=9, height=480, margin=dict(l=0, r=0, t=10, b=0),
        title="Candidate change locations · geographic context from OpenStreetMap"
    )
    st.plotly_chart(map_fig, use_container_width=True)

    report = pd.DataFrame([{
        "study_area": preset if "preset" in locals() else "Punjab AOI",
        "pre_scene_id": pre_item.id,
        "pre_date_utc": item_date(pre_item).isoformat(),
        "post_scene_id": post_item.id,
        "post_date_utc": item_date(post_item).isoformat(),
        "relative_orbit_pre": pre_item.properties.get("sat:relative_orbit"),
        "relative_orbit_post": post_item.properties.get("sat:relative_orbit"),
        "vv_threshold_db": result["threshold"],
        "minimum_backscatter_drop_db": result["min_change"],
        "candidate_pixels": int(result["candidates"].sum()),
        "approx_candidate_area_km2": round(result["area_km2"], 4),
        "interpretation": "Preliminary SAR change candidates; not validated flood extent",
    }])
    st.download_button("Download analysis metadata (CSV)", report.to_csv(index=False), "floodvision_sentinel1_report.csv", "text/csv")
    st.markdown("**Source:** Sentinel-1 RTC via [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc). Basemap © OpenStreetMap contributors. This workflow uses a simple VV threshold and pre/post change rule; it is not a trained AI model and requires validation against reference data.")

with st.expander("Method, assumptions and limitations"):
    st.markdown("""
- The app searches the public STAC catalog for Sentinel-1 RTC scenes intersecting the selected Punjab bounding box and date windows.
- It tries to select a pre/post pair with the same relative orbit, then compares VV radar backscatter on a common grid.
- Candidate pixels satisfy both a low post-event VV threshold and a decrease in backscatter relative to the pre-event scene.
- This heuristic can flag calm water but can also misclassify shadows, smooth surfaces, fields, or changes in soil moisture. It can miss flooding under vegetation or in built-up areas.
- No roads, buildings, or settlement exposure counts are claimed in this version. Those require a separate, sourced infrastructure layer and spatial validation.
- Historical acquisition coverage and the selected dates may not align exactly with the peak flood. Inspect scene dates before interpreting results.
""")
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

