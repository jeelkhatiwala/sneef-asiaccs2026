# SNEEF: Symbolic-Neural Evidence Extraction Framework

This repository provides supplementary material for the paper:

**"Bridging Symbolic Context and Neural Reasoning: A Hybrid Framework for Digital Evidence Extraction from Mobile Devices"**  
(Submitted to ACM ASIACCS 2026)

---

## Repository Structure

- `Android/` — All experiments on the Android forensic dataset
  - `RQ1/` Accuracy comparison
  - `RQ2/` Generalizability across apps
  - `RQ3-SchemaOnly/` Schema-only ablation
  - `RQ3-ValueOnly/` Values-only ablation
  - `RQ4/` Scalability (small, medium, large datasets)

- `iOS/` — All experiments on the iOS forensic dataset
  - Same structure as Android

- `paper/` — LaTeX source and figures of the paper

- `results/` — Aggregated plots and tables across both platforms

---

## Dataset Notes

- **Android**: 73 apps, 1,046 databases, 2,575 tables, ~59k rows (filtered ~22k).  
- **iOS**: 46 apps, 892 databases, 2,512 tables, ~181k rows (filtered ~30k).  

Only sanitized sample rows are shared here. Original forensic images cannot be redistributed.

