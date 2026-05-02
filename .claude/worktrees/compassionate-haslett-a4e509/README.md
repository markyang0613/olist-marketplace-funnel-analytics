# Olist Marketplace Funnel Analytics
**A Two-Sided Market Health Monitoring System**

## Executive Summary

This project builds a full-stack analytics framework on the Olist Brazilian E-Commerce dataset (100k+ orders) modelled after how a marketplace operations team at a company like **Karrot (당근마켓)** would monitor and investigate platform health.

The analysis is organized across five layers — from top-level health alerts down to cross-side network effect quantification — with a metric definitions document that serves as the analytical playbook.

### Key Findings Across All Layers

| Finding | Value |
|---------|-------|
| Platform GMV peak (May 2018) | R$977K/month |
| 6-Month GMV Forecast (Jan 2019) | R$1.2M (90% CI: R$1.06M–R$1.35M) |
| Buyer-to-Seller Ratio (mature months) | ~5–8x |
| Completion Rate (steady state) | ~93–96% |
| Month-1 Buyer Retention | 7.1% |
| Month-6 Buyer Retention | 0.3% |
| Monthly Seller Churn Rate | ~25–33% |
| Sellers at High/Critical Churn Risk | 1,050 sellers (33.9%) |
| Most Demand-Constrained Category | watches_gifts (10.3 orders/seller/month) |
| Most Supply-Saturated Category | auto (2.8 orders/seller/month) |
| Delivery time → review score | **Linear**: >20 days → near-certain 1★ rating |
| Regional delivery variance | **236%** between SP (fastest) and RR/AP (slowest) |

---

## Project Architecture

```
olist-marketplace-funnel-analytics/
├── data/                          # Raw Olist CSVs (7 tables)
├── notebooks/
│   ├── eda_visualizations.ipynb   # Original EDA: logistics & satisfaction
│   ├── 01_marketplace_health.ipynb    # Layer 1: Health dashboard
│   ├── 02_drilldown_analysis.ipynb    # Layer 2: Root cause drill-down
│   ├── 03_forecasting.ipynb           # Layer 3: Forecast & anomaly detection
│   └── 04_two_sided_market.ipynb      # Layer 4: Cross-side network effects
├── sql/                           # DuckDB SQL queries for all KPIs
├── images/                        # All generated visualizations
├── scripts/
│   └── create_notebooks.py        # Notebook generation script
├── METRIC_DEFINITIONS.md          # Full metric playbook (Layer 5)
├── requirements.txt
└── olist.db                       # DuckDB local warehouse
```

---

## Tech Stack

- **Database:** DuckDB (local OLAP warehouse)
- **Language:** Python 3.9 (pandas, numpy, matplotlib, seaborn, scipy)
- **Forecasting:** Prophet (Facebook), statsmodels
- **Environment:** Jupyter Notebooks
- **Version Control:** Git/GitHub

---

## Notebook Guide

### Pre-existing Analysis

#### `eda_visualizations.ipynb` — Logistics & Satisfaction EDA
The original analysis establishing the core business problem.
- **Regional Delivery Performance:** State-by-state delivery times (RR/AP worst at 25–30 days)
- **Delivery Time vs. Review Score:** Linear correlation — deliveries >20 days → near-certain 1★
- **A/B Simulation:** Reducing Northern Brazil to national avg (12.5d) → +16% review score in affected regions

---

### New Analysis (5-Layer Framework)

#### `01_marketplace_health.ipynb` — Layer 1: Health Dashboard (이상이 있나?)

The top-level ops dashboard. Answers: *"Is anything broken right now?"*

**Visualizations produced:**

| Image | Description |
|-------|-------------|
| `gmv_anomaly.png` | Monthly GMV with ±2σ rolling band and anomaly flags |
| `supply_demand_balance.png` | Active buyers vs. sellers + buyer/seller ratio |
| `completion_rate.png` | Monthly completion rate with cancellation overlay |
| `supply_demand_by_category.png` | Orders per active seller by top-10 category |

**Key insights:**
- GMV grew steadily from R$40K/month (Oct 2016) to R$977K/month (May 2018) with no statistical anomalies in the main growth period
- Buyer-to-seller ratio grew from ~2.2x to ~8x — demand outpaced supply acquisition
- Completion rate stabilised at ~93–96% after the first months; watches_gifts is the most demand-constrained category (10.3 orders/seller)

---

#### `02_drilldown_analysis.ipynb` — Layer 2: Drill-Down (어디가 원인인가?)

When Layer 1 flags an anomaly, this notebook isolates the root cause.

**Visualizations produced:**

| Image | Description |
|-------|-------------|
| `gmv_by_category.png` | Stacked GMV by category (top 10) over time |
| `gmv_by_region.png` | GMV trend by state + MoM % change heatmap |
| `seller_health.png` | New vs. churned sellers + churn rate + quality distribution |
| `cohort_retention.png` | Buyer cohort retention heatmap (first-purchase month vs. months later) |
| `matching_efficiency.png` | Orders/seller time series + category ranking |

**Key insights:**
- Month-1 buyer retention averages **7.1%** — highly transactional, low-loyalty pattern
- Seller churn runs at **25–33% monthly** — sellers frequently one-and-done on the platform
- bed_bath_table and health_beauty dominate GMV; São Paulo accounts for the majority of regional volume
- Median seller quality score: **0.976** — established sellers are generally high quality

---

#### `03_forecasting.ipynb` — Layer 3: Prediction (앞으로 어떻게 될까?)

Forward-looking signals for the operations team.

**Visualizations produced:**

| Image | Description |
|-------|-------------|
| `gmv_forecast.png` | Prophet GMV forecast with 90% confidence interval (6-month horizon) |
| `seller_churn_risk.png` | Seller churn risk distribution + at-risk sellers scatter |
| `anomaly_dashboard.png` | Rolling z-score panel across all 5 key metrics |

**Key insights:**
- Prophet forecasts GMV growing to **R$1.2M/month** by January 2019 (90% CI: R$1.06M–R$1.35M)
- **1,050 sellers (33.9%)** are classified as High or Critical churn risk based on volume decline, inactivity, and review score
- The anomaly dashboard reveals no sustained out-of-band periods on completion rate or review score — the platform's operational baseline is stable

---

#### `04_two_sided_market.ipynb` — Layer 4: Two-Sided Market (양면 시장)

Quantifies how supply-side changes propagate to demand-side outcomes.

**Visualizations produced:**

| Image | Description |
|-------|-------------|
| `seller_count_vs_conversion.png` | Seller count MoM change vs. completion rate change (scatter + OLS) |
| `new_seller_effect.png` | New sellers (<60d tenure) vs. established sellers: price & review comparison |
| `network_effects.png` | Seller density vs. buyer retention by category + top-15 retention ranking |

**Key insights:**
- **Seller count → completion rate:** r=–0.33 (p=0.15) — negative correlation is directionally intuitive (more sellers → more capacity → better completion) but does not reach significance at 95%, likely due to the short time series (21 months)
- **New seller effect on price:** New sellers (<60d) charge *higher* prices on average (R$135 vs R$115) — they are not competing purely on price; this may reflect category mix differences
- **Cross-side network effect:** Seller density positively correlates with buyer retention (r=0.21) — consistent with the hypothesis but short of statistical significance; more data would sharpen this signal

---

#### `METRIC_DEFINITIONS.md` — Layer 5: Metric Playbook

A reference document for analysts and AI agents covering all 12 KPIs:

- Precise definition and business rationale
- Pandas and SQL computation logic
- Alert thresholds
- Full L1 → L2 → L3 drill-down path per metric

---

## How to Run

```bash
# 1. Clone the repo and install dependencies
pip install -r requirements.txt

# 2. Run notebooks in order
jupyter notebook

# 3. Or regenerate all notebooks from scratch
python3 scripts/create_notebooks.py
```

**Execution order:** `01` → `02` → `03` → `04` (each is self-contained but follows the diagnostic flow)

---

## Dataset

**Source:** [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Kaggle)
- 100k+ orders, Sep 2016 – Oct 2018
- 96k unique customers, 3k sellers, 32k products across 71 categories
- 27 Brazilian states

---

## Analytical Framework

```
L1 — HEALTH CHECK (이상이 있나?)
     GMV, active users, completion rate, supply/demand ratio
          │
          ▼ anomaly detected
L2 — DRILL DOWN (어디가 원인인가?)
     Category/region decomposition, seller churn, cohort retention
          │
          ▼
L3 — FORECASTING (앞으로 어떻게 될까?)
     Prophet GMV forecast, seller churn risk, anomaly dashboard
          │
          ▼
L4 — TWO-SIDED MARKET (양면 시장)
     Supply shock → demand impact, new seller effects, network effects
          │
          ▼
L5 — METRIC PLAYBOOK (METRIC_DEFINITIONS.md)
     Definitions, SQL, thresholds, drill-down paths
```
