# FloodVision AI

FloodVision AI is an educational prototype dashboard concept for reviewing flood-related change, potentially exposed infrastructure, and settlements requiring road-connectivity checks.

## Current status — read carefully
This repository currently contains a **UI prototype with synthetic illustrative data only**. It does not yet download or process Sentinel imagery, run a trained flood segmentation model, or calculate verified disconnected settlements. Never use it for real rescue decisions.

## Run locally
Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
streamlit run app.py
```

## Intended next steps
1. Integrate Sentinel-1 pre/post-event imagery from Copernicus Data Space and compare compatible acquisitions from the same orbit track.
2. Add optional Sentinel-2 corroboration where cloud conditions permit.
3. Use a pre-event OpenStreetMap snapshot (e.g. via ohsome API) for buildings, roads, and bridges.
4. Add flood segmentation using a cited dataset such as Kuro Siwo; evaluate on held-out Himalayan scenes.
5. Build road-network connectivity analysis to identify settlements that may lack a route to a selected hospital/town.
6. Compare outputs against Copernicus EMSR927 only for evaluation, never as model input.
7. Add uncertainty reporting, a one-page report, and tests.

## Data attribution requirements when applicable
- “Contains modified Copernicus Sentinel data 2026.”
- “Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.”
- “© OpenStreetMap contributors.”
- Cite any training data actually used. If Kuro Siwo is used, cite Bountos et al. (2024). Do not claim to use a dataset until it has been integrated.

## Responsible use
This is an educational prototype, not an operational emergency-management tool. Satellite revisit intervals, terrain effects, clouds, and incomplete infrastructure data limit reliability.
