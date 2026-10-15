# FloodVision AI — report outline

## Problem
Flooding can damage transport infrastructure and isolate settlements. The goal is to support analysts with satellite-derived change mapping and road connectivity checks.

## Current implementation
The submitted prototype demonstrates a dashboard UI using synthetic illustrative locations and values. It is not a satellite-processing system yet.

## Proposed pipeline
1. Input area and flood date.
2. Find suitable pre/post Sentinel-1 scenes, prioritizing the same orbit track and comparable acquisition geometry.
3. Apply preprocessing and change detection / trained segmentation.
4. Overlay a pre-event OpenStreetMap snapshot.
5. Estimate potentially exposed assets.
6. Remove/flag disrupted road edges and test routes from settlements to hospitals/towns.
7. Produce a map and a report whose numeric claims are generated from computed outputs.

## Evaluation plan
Compare flood extent and affected assets with EMSR927 after model outputs are generated. Reference maps are for checking only and must not be used as model inputs.

## Limitations
The current demo uses synthetic data only. It has no trained model, real satellite processing, or validated connectivity results. Even a future implementation cannot provide minute-ahead warning for sudden glacier collapse; radar geometry, revisit times, terrain, and map completeness affect results.

## Attribution
Add the required Copernicus Sentinel, WorldDEM-30, and OpenStreetMap statements when those data are actually used. Cite every training dataset integrated.
