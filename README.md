FloodVision AI — Sentinel-1 real-data prototype

This version queries the public Microsoft Planetary Computer STAC catalog for Sentinel-1 RTC scenes and performs a simple pre/post-event VV backscatter change screen for two Punjab AOIs.

Run on macOS
Use the same virtual environment that already runs Streamlit:
cd ~/Downloads/FloodVision_AI
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
Back up the original first, then replace app.py and requirements.txt with these versions.
Data and method

- Sentinel-1 RTC imagery is retrieved from the public Microsoft Planetary Computer STAC API.
- Default historical date windows are June 15–July 5, 2023 (pre-event) and July 8–25, 2023 (post-event). The app reports actual scene dates found and allows date changes.
- Candidate pixels require post-event VV below the selected threshold and a drop in VV relative to the pre-event scene.
- This is a heuristic screening method, not a trained model or validated flood extent. Do not use for emergency decisions.

- Map basemap attribution: © OpenStreetMap contributors.

  Sources
- Sentinel-1 RTC: https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc
- Planetary Computer STAC API: https://planetarycomputer.microsoft.com/api/stac/v1
- Copernicus Data Space Sentinel Hub documentation: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview.html
