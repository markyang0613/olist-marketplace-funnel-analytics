# Metric Definitions — Olist Marketplace Analytics

> **Purpose:** This document is the authoritative reference for every KPI used in this project.
> It is structured so an analyst (or AI agent) can look up: what a metric means, how to compute it,
> where to find the code, the alert threshold, and the drill-down path when it degrades.

---

## Table of Contents

1. [Gross Merchandise Value (GMV)](#1-gross-merchandise-value-gmv)
2. [Active Buyer Count](#2-active-buyer-count)
3. [Active Seller Count](#3-active-seller-count)
4. [Buyer-to-Seller Ratio](#4-buyer-to-seller-ratio)
5. [Transaction Completion Rate](#5-transaction-completion-rate)
6. [Supply/Demand Ratio (Matching Efficiency)](#6-supplydemand-ratio-matching-efficiency)
7. [Seller Churn Rate](#7-seller-churn-rate)
8. [Seller Listing Quality Score](#8-seller-listing-quality-score)
9. [Buyer Cohort Retention Rate](#9-buyer-cohort-retention-rate)
10. [Seller Churn Risk Score](#10-seller-churn-risk-score)
11. [Cross-Side Network Effect Proxy](#11-cross-side-network-effect-proxy)
12. [GMV Anomaly Flag (Z-Score)](#12-gmv-anomaly-flag-z-score)

---

## 1. Gross Merchandise Value (GMV)

**Definition:** Total value of items sold (sum of item prices) on delivered orders within a time period.

**Why it matters:** GMV is the primary top-line health metric for a marketplace. It reflects the aggregate economic activity facilitated by the platform.

**Unit:** Brazilian Real (BRL)

**Pandas computation:**
```python
orders_items = orders.merge(order_items[['order_id', 'price']], on='order_id')
gmv_monthly = (
    orders_items[orders_items['order_status'] == 'delivered']
    .groupby(orders_items['order_purchase_timestamp'].dt.to_period('M'))['price']
    .sum()
)
```

**SQL equivalent:**
```sql
SELECT
    DATE_TRUNC('month', order_purchase_timestamp) AS month,
    SUM(price) AS gmv
FROM orders
JOIN order_items USING (order_id)
WHERE order_status = 'delivered'
GROUP BY 1
ORDER BY 1;
```

**Anomaly threshold:** Monthly rolling z-score |z| > 2 (3-month window) → trigger alert

**Drill-down path (L1 → L2 → L3):**
- L1: Is monthly GMV anomalous?
- L2a: Which categories are contributing to the drop? → `gmv_by_category.png`
- L2b: Which regions are declining? → `gmv_by_region.png`
- L2c: Is the drop supply-side (seller churn) or demand-side (buyer drop-off)?
- L3: Use Prophet forecast to project recovery timeline → `gmv_forecast.png`

---

## 2. Active Buyer Count

**Definition:** Number of unique customers (`customer_unique_id`) who placed at least one order in a given month.

**Why it matters:** Demand-side health indicator. Declining active buyers signal buyer erosion — either from poor experience, competitive loss, or insufficient supply.

**Note:** `customer_id` is order-specific; `customer_unique_id` is the canonical user identity across orders.

**Pandas computation:**
```python
orders_cust = orders.merge(customers[['customer_id', 'customer_unique_id']], on='customer_id')
active_buyers = (
    orders_cust
    .groupby(orders_cust['order_purchase_timestamp'].dt.to_period('M'))['customer_unique_id']
    .nunique()
)
```

**Anomaly threshold:** MoM decline > 15%, or rolling z-score |z| > 2

**Drill-down path:**
- L2: Which cohorts are declining? → Cohort retention matrix
- L2: Which categories are losing buyers?
- L3: Is the decline correlated with a supply shock? → `seller_count_vs_conversion.png`

---

## 3. Active Seller Count

**Definition:** Number of unique sellers (`seller_id`) who had at least one item sold (in `order_items`) in a given month.

**Why it matters:** Supply-side health indicator. A falling seller count directly reduces category coverage, leading to unmet buyer demand.

**Pandas computation:**
```python
orders_sell = orders.merge(order_items[['order_id', 'seller_id']], on='order_id')
active_sellers = (
    orders_sell
    .groupby(orders_sell['order_purchase_timestamp'].dt.to_period('M'))['seller_id']
    .nunique()
)
```

**Anomaly threshold:** MoM decline > 10%, or rolling z-score |z| > 2

**Drill-down path:**
- L2: Decompose into churn (existing sellers leaving) vs. acquisition (new sellers entering)
- L2: Which categories are losing sellers?
- L3: Seller churn risk list → `seller_churn_risk.png`

---

## 4. Buyer-to-Seller Ratio

**Definition:** `active_buyers / active_sellers` per month. Measures demand intensity per unit of supply.

**Why it matters:**
- Rising ratio → demand outpacing supply → opportunity to acquire new sellers before buyers experience scarcity
- Falling ratio → supply surplus → focus on demand stimulation (promotions, marketing)

**Pandas computation:**
```python
ratio = active_buyers / active_sellers  # Series, indexed by month
```

**Healthy range:** Stable within ±20% of the historical average

**Anomaly threshold:** Sustained rise > 20% above trailing 3-month average

---

## 5. Transaction Completion Rate

**Definition:** `delivered_orders / total_orders_placed` in a given month.

**Why it matters:** Every non-delivered order is a failed transaction — a buyer who paid but didn't receive. This damages trust, increases support costs, and drives churn.

**Pandas computation:**
```python
completion_rate = (
    orders.groupby('month')
    .apply(lambda x: (x['order_status'] == 'delivered').sum() / len(x))
)
```

**SQL equivalent:**
```sql
SELECT
    DATE_TRUNC('month', order_purchase_timestamp) AS month,
    COUNT(CASE WHEN order_status = 'delivered' THEN 1 END) * 1.0 / COUNT(*) AS completion_rate
FROM orders
GROUP BY 1;
```

**Alert threshold:** Falls below 90% in any month → escalate to operations

**Drill-down path:**
- L2: Is the drop in one region or nationwide?
- L2: Is the drop correlated with a seller churn event?
- L3: Rolling z-score anomaly dashboard → `anomaly_dashboard.png`

---

## 6. Supply/Demand Ratio (Matching Efficiency)

**Definition:** `orders / active_sellers` per category per month. Measures how efficiently supply is absorbing demand within each category.

**Why it matters:** A category with 2 sellers and 50 orders has poor supply coverage. One with 30 sellers and 10 orders is over-supplied. Matching efficiency guides where to acquire sellers vs. where to stimulate demand.

**Pandas computation:**
```python
cat_monthly = (
    filtered_items
    .groupby(['month', 'category'])
    .agg(demand=('order_id', 'nunique'), supply=('seller_id', 'nunique'))
    .reset_index()
)
cat_monthly['orders_per_seller'] = cat_monthly['demand'] / cat_monthly['supply']
```

**Thresholds:**
- `orders_per_seller < 3` → over-supplied → stimulate demand
- `orders_per_seller > 10` → under-supplied → acquire more sellers
- Normal range: 3–10

**Drill-down path:**
- L1: Category-level dashboard → `supply_demand_by_category.png`
- L2: Matching efficiency time series → `matching_efficiency.png`
- L4: Is low efficiency correlated with low buyer retention? → `network_effects.png`

---

## 7. Seller Churn Rate

**Definition:** `churned_sellers / active_sellers_in_prior_month` per month.
A seller "churns" if they were active in month T-1 but have zero sales in month T.

**Why it matters:** Seller churn directly reduces supply coverage. High churn also signals
platform health issues — poor seller experience, low earnings, or competition from other platforms.

**Pandas computation:**
```python
# For each consecutive month pair:
prev_sellers = set(seller_months[seller_months['year_month'] == prev]['seller_id'])
curr_sellers = set(seller_months[seller_months['year_month'] == curr]['seller_id'])
churned = len(prev_sellers - curr_sellers)
churn_rate = churned / len(prev_sellers)
```

**Alert threshold:** Monthly churn rate > 20% → investigate root cause

**Drill-down path:**
- L2: Visualise new vs. churned sellers per month → `seller_health.png`
- L3: Identify at-risk sellers before they churn → `seller_churn_risk.png`

---

## 8. Seller Listing Quality Score

**Definition:** Composite score per seller:
`quality_score = 0.5 × (avg_review_score / 5) + 0.5 × fulfillment_rate`

Where `fulfillment_rate = delivered_orders / total_orders`.

**Range:** 0.0 (worst) to 1.0 (best)

**Why it matters:** Quality scores predict future buyer satisfaction. Low-quality sellers drive
negative reviews and buyer churn, even if they maintain volume.

**Pandas computation:**
```python
seller_quality = (
    base[base['order_status'] == 'delivered']
    .merge(reviews[['order_id', 'review_score']], on='order_id', how='left')
    .groupby('seller_id')
    .agg(avg_review=('review_score', 'mean'),
         fulfillment_rate=('order_status', lambda x: (x == 'delivered').sum() / len(x)))
)
seller_quality['quality_score'] = (seller_quality['avg_review'] / 5) * 0.5 + seller_quality['fulfillment_rate'] * 0.5
```

**Thresholds:**
- `quality_score < 0.6` → at-risk seller → flag for review
- `quality_score > 0.85` → high-quality → consider for promotion/featured placement

---

## 9. Buyer Cohort Retention Rate

**Definition:** For a cohort of buyers defined by their first purchase month, the % who make
at least one additional purchase in month N.

`retention[cohort, N] = buyers_active_in_month_N / cohort_size`

**Why it matters:** Retention is the single most important demand-side metric. It reveals
whether the platform generates repeat behavior (loyalty model) or is purely transactional
(acquisition model). Olist's 3.12% repeat rate indicates the latter.

**Pandas computation:**
```python
# Assign each customer to their first purchase cohort
first_purchase = cust_orders.groupby('customer_unique_id')['order_month'].min()
cust_orders = cust_orders.merge(first_purchase.rename('cohort_month'), on='customer_unique_id')
cust_orders['months_since_first'] = (cust_orders['order_month'] - cust_orders['cohort_month']).apply(lambda x: x.n)

# Build retention matrix
cohort_size = cust_orders[cust_orders['months_since_first'] == 0].groupby('cohort_month')['customer_unique_id'].nunique()
retention_pivot = cust_orders.groupby(['cohort_month', 'months_since_first'])['customer_unique_id'].nunique().unstack()
retention_rate = retention_pivot.divide(cohort_size, axis=0)
```

**Healthy benchmark:** Month-1 retention ≥ 10%, Month-6 retention ≥ 5%

**Drill-down path:**
- L2: Which cohorts have lowest retention? → `cohort_retention.png`
- L4: Is retention higher in categories with more sellers? → `network_effects.png`

---

## 10. Seller Churn Risk Score

**Definition:** Rule-based 0–3 flag count per seller. A seller gets +1 for each of:
1. Orders in last 30 days ≤ 50% of their 6-month monthly average (volume drop)
2. No orders in the last 45 days (inactivity)
3. Average review score < 3.5 (quality warning)

**Risk labels:**
- 0 flags → Low
- 1 flag → Medium
- 2 flags → High
- 3 flags → Critical

**Pandas computation:**
```python
seller_stats['flag_volume_drop'] = (
    (seller_stats['orders_last_30d'] <= seller_stats['avg_monthly_hist'] * 0.5) &
    (seller_stats['avg_monthly_hist'] > 0)
)
seller_stats['flag_inactive'] = seller_stats['days_since_last'] >= 45
seller_stats['flag_low_review'] = seller_stats['avg_review'] < 3.5
seller_stats['risk_flags'] = (flag_volume_drop + flag_inactive + flag_low_review).astype(int)
```

**Operational use:**
- Export `High` + `Critical` sellers monthly to seller success team
- Trigger automated outreach email for `High` risk sellers
- Escalate `Critical` to account manager

---

## 11. Cross-Side Network Effect Proxy

**Definition:** Pearson correlation between seller density (avg active sellers/month in a category)
and buyer retention rate in that category.

A **positive** and statistically significant correlation (p < 0.05) confirms that
supply-side growth drives demand-side loyalty — the core cross-side network effect of a marketplace.

**Pandas computation:**
```python
# Per category
cat_density = (
    base[base['order_status'] == 'delivered']
    .groupby(['month', 'category'])['seller_id'].nunique()
    .groupby('category').mean()
    .rename('avg_sellers')
)

cat_retention = (
    base[base['order_status'] == 'delivered']
    .groupby(['category', 'customer_unique_id'])['order_id'].nunique()
    .groupby('category').apply(lambda g: (g > 1).sum() / len(g))
    .rename('buyer_retention_rate')
)

r, p = scipy.stats.pearsonr(cat_density, cat_retention)
```

**Interpretation:**
- r > 0.3, p < 0.05 → supply-side investment drives buyer loyalty → **prioritize seller acquisition**
- r ≈ 0 → no cross-side effect detected → **focus on independent demand campaigns**

---

## 12. GMV Anomaly Flag (Z-Score)

**Definition:** For each month, the z-score of GMV relative to a centered rolling window:
`z = (GMV_t - rolling_mean) / rolling_std`

Computed with a 3-month centered window (`min_periods=2`).

**Alert rule:** If |z| > 2, flag as anomaly → trigger investigation protocol.

**Pandas computation:**
```python
gmv_monthly['roll_mean'] = gmv_monthly['gmv'].rolling(3, center=True, min_periods=2).mean()
gmv_monthly['roll_std']  = gmv_monthly['gmv'].rolling(3, center=True, min_periods=2).std()
gmv_monthly['z_score']   = (gmv_monthly['gmv'] - gmv_monthly['roll_mean']) / gmv_monthly['roll_std']
gmv_monthly['anomaly']   = gmv_monthly['z_score'].abs() > 2
```

**The same method is applied across all metrics in the anomaly dashboard** (`03_forecasting.ipynb`),
using window=4 months for smoother detection on the full metric set.

---

## Drill-Down Reference Map

```
L1: Health Check (01_marketplace_health.ipynb)
├── GMV anomaly? ──────────────────────────────► L2: Category decomposition (02_drilldown_analysis.ipynb §2.1)
│                                                L2: Region decomposition       (02_drilldown_analysis.ipynb §2.2)
│                                                L3: Prophet forecast           (03_forecasting.ipynb §3.1)
│
├── Active buyer count falling? ───────────────► L2: Cohort retention           (02_drilldown_analysis.ipynb §2.4)
│                                                L4: Seller density correlation (04_two_sided_market.ipynb §4.3)
│
├── Active seller count falling? ──────────────► L2: Churn rate & acquisition   (02_drilldown_analysis.ipynb §2.3)
│                                                L3: Seller churn risk list     (03_forecasting.ipynb §3.2)
│
├── Completion rate falling? ──────────────────► L2: Regional breakdown         (existing SQL)
│                                                L4: Seller count correlation   (04_two_sided_market.ipynb §4.1)
│
└── Category supply/demand imbalanced? ────────► L2: Matching efficiency        (02_drilldown_analysis.ipynb §2.5)
                                                 L4: New seller price/quality   (04_two_sided_market.ipynb §4.2)
```

---

## Data Sources

| Table | File | Key Columns |
|-------|------|-------------|
| orders | `olist_orders_dataset.csv` | `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp` |
| order_items | `olist_order_items_dataset.csv` | `order_id`, `seller_id`, `price`, `freight_value` |
| customers | `olist_customers_dataset.csv` | `customer_id`, `customer_unique_id`, `customer_state` |
| sellers | `olist_sellers_dataset.csv` | `seller_id`, `seller_state` |
| products | `olist_products_dataset.csv` | `product_id`, `product_category_name` |
| order_reviews | `olist_order_reviews_dataset.csv` | `order_id`, `review_score` |
| category_name_translation | `product_category_name_translation.csv` | `product_category_name`, `product_category_name_english` |

---

*Last updated: 2026-05-01 | Dataset: Olist Brazilian E-Commerce (Kaggle)*
