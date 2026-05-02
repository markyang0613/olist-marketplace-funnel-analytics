"""
Generates all four analysis notebooks for the Olist Marketplace project.
Run from the project root: python3 scripts/create_notebooks.py
"""
import nbformat as nbf
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NB_DIR = os.path.join(ROOT, "notebooks")
os.makedirs(NB_DIR, exist_ok=True)


def md(source): return nbf.v4.new_markdown_cell(source)
def code(source): return nbf.v4.new_code_cell(source)


def make_meta():
    return {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.9.0"}
    }


# ─────────────────────────────────────────────────────────────────────────────
# NOTEBOOK 1 — Layer 1: Marketplace Health Dashboard
# ─────────────────────────────────────────────────────────────────────────────
def build_nb1():
    nb = nbf.v4.new_notebook(metadata=make_meta())
    nb.cells = [

        md("""# Layer 1: Marketplace Health Dashboard (이상이 있나?)

## Why This Analysis Matters
In a two-sided marketplace, problems on either side propagate quickly to the other.
A sudden GMV drop could mean seller churn, buyer drop-off, or operational collapse —
but without a health dashboard you can't tell which.

This notebook answers: **Is anything abnormal right now?**

**Metrics:**
- Monthly GMV trend with statistical anomaly flags (rolling z-score)
- Active seller count vs. active buyer count over time
- Transaction completion rate trend
- Supply/demand balance by category (orders per active seller)
"""),

        code("""\
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams['figure.dpi'] = 120

orders = pd.read_csv('../data/olist_orders_dataset.csv',
    parse_dates=['order_purchase_timestamp','order_approved_at',
                 'order_delivered_carrier_date','order_delivered_customer_date',
                 'order_estimated_delivery_date'])
order_items   = pd.read_csv('../data/olist_order_items_dataset.csv')
customers     = pd.read_csv('../data/olist_customers_dataset.csv')
products      = pd.read_csv('../data/olist_products_dataset.csv')
category_trans= pd.read_csv('../data/product_category_name_translation.csv')

print(f"Orders: {len(orders):,}  Items: {len(order_items):,}  "
      f"Customers: {len(customers):,}")
"""),

        md("""## 1. Monthly GMV Trend with Anomaly Detection

**Definition:** GMV = sum of item prices on delivered orders, aggregated monthly.

**Anomaly rule:** Flag any month where the 3-month rolling z-score |z| > 2.
This catches sudden drops or spikes that deviate more than 2 standard deviations
from the recent trend — a standard threshold for operational alerts.
"""),

        code("""\
orders_items = orders.merge(
    order_items[['order_id','price','seller_id']], on='order_id')
orders_items['month'] = (orders_items['order_purchase_timestamp']
                         .dt.to_period('M').dt.to_timestamp())

gmv_monthly = (orders_items[orders_items['order_status'] == 'delivered']
               .groupby('month')['price'].sum()
               .reset_index(name='gmv'))
# Trim first/last months (partial data)
gmv_monthly = gmv_monthly.iloc[1:-1].copy().reset_index(drop=True)

# Rolling z-score (window = 3)
W = 3
gmv_monthly['roll_mean'] = gmv_monthly['gmv'].rolling(W, center=True, min_periods=2).mean()
gmv_monthly['roll_std']  = gmv_monthly['gmv'].rolling(W, center=True, min_periods=2).std()
gmv_monthly['z_score']   = ((gmv_monthly['gmv'] - gmv_monthly['roll_mean'])
                             / gmv_monthly['roll_std'])
gmv_monthly['anomaly']   = gmv_monthly['z_score'].abs() > 2

print(gmv_monthly[['month','gmv','z_score','anomaly']].to_string(index=False))
"""),

        code("""\
fig, ax = plt.subplots(figsize=(14, 6))

ax.fill_between(gmv_monthly['month'],
    gmv_monthly['roll_mean'] - 2 * gmv_monthly['roll_std'],
    gmv_monthly['roll_mean'] + 2 * gmv_monthly['roll_std'],
    alpha=0.15, color='steelblue', label='±2 Std Dev Band')

ax.plot(gmv_monthly['month'], gmv_monthly['gmv'],
        marker='o', color='steelblue', linewidth=2, label='Monthly GMV')
ax.plot(gmv_monthly['month'], gmv_monthly['roll_mean'],
        color='navy', linestyle='--', linewidth=1.5, label='3-Month Rolling Mean')

anomalies = gmv_monthly[gmv_monthly['anomaly']]
ax.scatter(anomalies['month'], anomalies['gmv'],
           color='red', zorder=5, s=140, marker='X', label='Anomaly (|z| > 2)')

ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.xticks(rotation=45)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'R${x/1e6:.1f}M'))
ax.set_title('Monthly GMV Trend with Anomaly Detection', fontsize=15, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('GMV (BRL)')
ax.legend()
plt.tight_layout()
plt.savefig('../images/gmv_anomaly.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## 2. Active Sellers vs. Active Buyers Over Time

**Active buyer:** customer with ≥1 order placed in that month.
**Active seller:** seller with ≥1 item sold in that month.

The buyer-to-seller ratio is a proxy for **demand intensity** — how hard each seller is
working to meet demand. Ratio rising rapidly = demand outpacing supply → opportunity
to onboard new sellers. Ratio falling = supply surplus → focus on demand stimulation.
"""),

        code("""\
orders_cust = orders.merge(
    customers[['customer_id','customer_unique_id']], on='customer_id')
orders_cust['month'] = (orders_cust['order_purchase_timestamp']
                        .dt.to_period('M').dt.to_timestamp())

active_buyers = (orders_cust.groupby('month')['customer_unique_id']
                 .nunique().reset_index(name='active_buyers'))

orders_sellers = orders.merge(
    order_items[['order_id','seller_id']], on='order_id')
orders_sellers['month'] = (orders_sellers['order_purchase_timestamp']
                            .dt.to_period('M').dt.to_timestamp())

active_sellers = (orders_sellers.groupby('month')['seller_id']
                  .nunique().reset_index(name='active_sellers'))

sd = (active_buyers.merge(active_sellers, on='month')
                   .iloc[1:-1].reset_index(drop=True))
sd['buyer_to_seller_ratio'] = sd['active_buyers'] / sd['active_sellers']
print(sd.to_string(index=False))
"""),

        code("""\
fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

axes[0].plot(sd['month'], sd['active_buyers'],
             color='#2196F3', marker='o', linewidth=2, label='Active Buyers')
axes[0].plot(sd['month'], sd['active_sellers'],
             color='#FF5722', marker='s', linewidth=2, label='Active Sellers')
axes[0].set_title('Active Buyers vs. Active Sellers Over Time',
                  fontsize=14, fontweight='bold')
axes[0].set_ylabel('Count')
axes[0].legend()

axes[1].fill_between(sd['month'], sd['buyer_to_seller_ratio'],
                     alpha=0.25, color='purple')
axes[1].plot(sd['month'], sd['buyer_to_seller_ratio'],
             color='purple', linewidth=2, label='Buyer/Seller Ratio')
avg_ratio = sd['buyer_to_seller_ratio'].mean()
axes[1].axhline(avg_ratio, linestyle='--', color='gray',
                label=f'Average: {avg_ratio:.1f}x')
axes[1].set_title('Buyer-to-Seller Ratio (Demand Intensity)',
                  fontsize=14, fontweight='bold')
axes[1].set_ylabel('Buyers per Seller')
axes[1].set_xlabel('Month')
axes[1].legend()

for ax in axes:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

plt.tight_layout()
plt.savefig('../images/supply_demand_balance.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## 3. Transaction Completion Rate Trend

**Completion rate** = delivered orders / all orders placed that month.
This is a core operational health metric. A declining trend signals:
- Seller-side: increasing cancellations or shipping failures
- Logistics: carrier breakdowns
- Fraud: more fraudulent orders being placed and later voided

Target threshold: >90% is considered healthy for most marketplaces.
"""),

        code("""\
orders['month'] = (orders['order_purchase_timestamp']
                   .dt.to_period('M').dt.to_timestamp())

def status_agg(g):
    return pd.Series({
        'total_orders': len(g),
        'delivered':    (g['order_status'] == 'delivered').sum(),
        'canceled':     (g['order_status'] == 'canceled').sum(),
    })

completion = (orders.groupby('month').apply(status_agg)
              .reset_index().iloc[1:-1].reset_index(drop=True))

completion['completion_rate'] = completion['delivered'] / completion['total_orders']
completion['cancel_rate']     = completion['canceled']  / completion['total_orders']
completion['completion_roll'] = (completion['completion_rate']
                                  .rolling(3, center=True, min_periods=2).mean())
print(completion[['month','total_orders','delivered',
                   'completion_rate','cancel_rate']].to_string(index=False))
"""),

        code("""\
fig, ax = plt.subplots(figsize=(14, 6))

ax.fill_between(completion['month'], completion['completion_rate'],
                alpha=0.12, color='green')
ax.plot(completion['month'], completion['completion_rate'],
        color='green', marker='o', linewidth=2, label='Completion Rate')
ax.plot(completion['month'], completion['completion_roll'],
        color='darkgreen', linestyle='--', linewidth=1.5,
        label='3-Month Rolling Avg')

ax2 = ax.twinx()
ax2.bar(completion['month'], completion['cancel_rate'] * 100,
        width=20, alpha=0.35, color='red', label='Cancellation Rate (%)')
ax2.set_ylabel('Cancellation Rate (%)', color='red')
ax2.tick_params(axis='y', colors='red')
ax2.set_ylim(0, 15)

ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.xticks(rotation=45)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))
ax.set_title('Transaction Completion Rate Over Time', fontsize=15, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('Completion Rate', color='green')
ax.tick_params(axis='y', colors='green')
ax.axhline(0.9, linestyle=':', color='orange', linewidth=1.5, label='90% Target')

lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc='lower left')

plt.tight_layout()
plt.savefig('../images/completion_rate.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## 4. Supply/Demand Ratio by Category

**Supply/demand ratio** = orders per active seller per month within a category.

- **High ratio (>10):** demand-constrained — few sellers competing for many orders.
  *Action: aggressive seller acquisition in this category.*
- **Low ratio (<3):** supply-saturated — many sellers chasing few orders.
  *Action: stimulate demand (promotions, marketing) or let over-supply self-correct.*
"""),

        code("""\
items_cat = (order_items
    .merge(products[['product_id','product_category_name']], on='product_id')
    .merge(category_trans, on='product_category_name', how='left'))
items_cat['category'] = (items_cat['product_category_name_english']
                         .fillna(items_cat['product_category_name']))

items_orders = items_cat.merge(
    orders[['order_id','order_purchase_timestamp','order_status']], on='order_id')
items_orders['month'] = (items_orders['order_purchase_timestamp']
                          .dt.to_period('M').dt.to_timestamp())

top_cats = items_cat['category'].value_counts().head(10).index.tolist()
filtered = (items_orders[(items_orders['category'].isin(top_cats)) &
                         (items_orders['order_status'] == 'delivered')])

cat_monthly = (filtered.groupby(['month','category'])
    .agg(demand=('order_id','nunique'), supply=('seller_id','nunique'))
    .reset_index())
cat_monthly = (cat_monthly[
    (cat_monthly['month'] > cat_monthly['month'].min()) &
    (cat_monthly['month'] < cat_monthly['month'].max())])
cat_monthly['orders_per_seller'] = cat_monthly['demand'] / cat_monthly['supply']

print("Average orders/seller by category:")
print(cat_monthly.groupby('category')['orders_per_seller']
      .mean().sort_values(ascending=False).round(2).to_string())
"""),

        code("""\
fig, ax = plt.subplots(figsize=(14, 7))
colors = plt.cm.tab10.colors

for i, cat in enumerate(top_cats):
    sub = cat_monthly[cat_monthly['category'] == cat]
    ax.plot(sub['month'], sub['orders_per_seller'],
            marker='.', linewidth=1.5, alpha=0.85, color=colors[i], label=cat)

ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.xticks(rotation=45)
ax.set_title('Supply/Demand Ratio by Category\\n(Orders per Active Seller per Month)',
             fontsize=14, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('Orders per Active Seller')
ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=9)
plt.tight_layout()
plt.savefig('../images/supply_demand_by_category.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## Layer 1 Health Summary

| Metric | Query | Alert Threshold |
|--------|-------|-----------------|
| GMV | Sum of item prices on delivered orders | Monthly z-score \\|z\\| > 2 |
| Active Buyers | Unique `customer_unique_id` per month | MoM drop > 15% |
| Active Sellers | Unique `seller_id` per month | MoM drop > 10% |
| Buyer/Seller Ratio | active_buyers / active_sellers | Sustained rise > 20% above avg |
| Completion Rate | delivered / total orders | Falls below 90% |
| Orders/Seller | orders ÷ active sellers per category | Category drops below 3 or spikes above 15 |

→ **Drill down into any flagged metric using `02_drilldown_analysis.ipynb`.**
"""),

    ]
    return nb


# ─────────────────────────────────────────────────────────────────────────────
# NOTEBOOK 2 — Layer 2: Drill-Down Analysis
# ─────────────────────────────────────────────────────────────────────────────
def build_nb2():
    nb = nbf.v4.new_notebook(metadata=make_meta())
    nb.cells = [

        md("""# Layer 2: Drill-Down Analysis (어디가 원인인가?)

## Why This Analysis Matters
When the Layer 1 dashboard flags an anomaly, you need to isolate the root cause
before making any intervention decision. This notebook provides structured drill-downs
across four dimensions:

1. **GMV Decomposition** — which categories or regions are driving a GMV shift?
2. **Seller-Side Health** — churn, new acquisition, listing quality
3. **Buyer-Side Health** — cohort retention, purchase funnel
4. **Matching Efficiency** — how well supply meets demand at the category level
"""),

        code("""\
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams['figure.dpi'] = 120

orders        = pd.read_csv('../data/olist_orders_dataset.csv',
    parse_dates=['order_purchase_timestamp','order_delivered_customer_date'])
order_items   = pd.read_csv('../data/olist_order_items_dataset.csv')
customers     = pd.read_csv('../data/olist_customers_dataset.csv')
sellers       = pd.read_csv('../data/olist_sellers_dataset.csv')
products      = pd.read_csv('../data/olist_products_dataset.csv')
reviews       = pd.read_csv('../data/olist_order_reviews_dataset.csv')
category_trans= pd.read_csv('../data/product_category_name_translation.csv')

# Build enriched orders table used throughout this notebook
orders['month'] = orders['order_purchase_timestamp'].dt.to_period('M').dt.to_timestamp()
orders['year_month'] = orders['order_purchase_timestamp'].dt.to_period('M')

items_cat = (order_items
    .merge(products[['product_id','product_category_name']], on='product_id', how='left')
    .merge(category_trans, on='product_category_name', how='left'))
items_cat['category'] = (items_cat['product_category_name_english']
                         .fillna(items_cat['product_category_name']))

base = (orders.merge(order_items[['order_id','price','seller_id']], on='order_id')
              .merge(customers[['customer_id','customer_unique_id','customer_state']],
                     on='customer_id'))
base = base.merge(items_cat[['order_id','category']].drop_duplicates(), on='order_id', how='left')

print(f"Enriched base table: {len(base):,} rows")
"""),

        md("""## 2.1 GMV Decomposition by Category

When GMV drops, the first question is: **which categories are falling?**
Here we plot the monthly GMV contribution per category for the top 10.
"""),

        code("""\
top_cats = (base[base['order_status']=='delivered']
            .groupby('category')['price'].sum()
            .nlargest(10).index.tolist())

gmv_cat = (base[(base['order_status']=='delivered') &
                (base['category'].isin(top_cats))]
           .groupby(['month','category'])['price']
           .sum().reset_index(name='gmv'))

# Trim partial months
gmv_cat = gmv_cat[
    (gmv_cat['month'] > gmv_cat['month'].min()) &
    (gmv_cat['month'] < gmv_cat['month'].max())]

fig, ax = plt.subplots(figsize=(15, 7))
colors = plt.cm.tab10.colors
for i, cat in enumerate(top_cats):
    sub = gmv_cat[gmv_cat['category'] == cat]
    ax.stackplot(sub['month'], sub['gmv'], labels=[cat], colors=[colors[i]], alpha=0.75)

ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.xticks(rotation=45)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'R${x/1e6:.1f}M'))
ax.set_title('Monthly GMV Decomposition by Category (Top 10)',
             fontsize=15, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('GMV (BRL)')
ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=9)
plt.tight_layout()
plt.savefig('../images/gmv_by_category.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## 2.2 GMV Decomposition by Region

Regional variation matters for logistics and seller network planning.
We look at GMV share by state and flag states with declining contribution.
"""),

        code("""\
gmv_state = (base[base['order_status']=='delivered']
             .groupby(['month','customer_state'])['price']
             .sum().reset_index(name='gmv'))

top_states = (base[base['order_status']=='delivered']
              .groupby('customer_state')['price'].sum()
              .nlargest(8).index.tolist())

gmv_state_top = gmv_state[
    (gmv_state['customer_state'].isin(top_states)) &
    (gmv_state['month'] > gmv_state['month'].min()) &
    (gmv_state['month'] < gmv_state['month'].max())]

# MoM % change heatmap
pivot = gmv_state_top.pivot(index='customer_state', columns='month', values='gmv').fillna(0)
pct_change = pivot.pct_change(axis=1).iloc[:, 1:] * 100

fig, axes = plt.subplots(1, 2, figsize=(18, 6))

# Left: absolute GMV
for i, state in enumerate(top_states):
    sub = gmv_state_top[gmv_state_top['customer_state'] == state]
    axes[0].plot(sub['month'], sub['gmv'], marker='.', linewidth=1.8,
                 label=state, color=plt.cm.Set1.colors[i % 9])
axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
axes[0].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45)
axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'R${x/1e6:.1f}M'))
axes[0].set_title('Monthly GMV by State (Top 8)', fontsize=13, fontweight='bold')
axes[0].set_xlabel('Month'); axes[0].set_ylabel('GMV (BRL)')
axes[0].legend(fontsize=9)

# Right: MoM % heatmap
sns.heatmap(pct_change, ax=axes[1], cmap='RdYlGn', center=0, fmt='.0f',
            annot=True, annot_kws={'size': 8}, linewidths=0.4,
            xticklabels=[m.strftime('%b %y') for m in pct_change.columns])
axes[1].set_title('Month-over-Month GMV Change by State (%)',
                  fontsize=13, fontweight='bold')
axes[1].set_xlabel('Month'); axes[1].set_ylabel('State')
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=45)

plt.tight_layout()
plt.savefig('../images/gmv_by_region.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## 2.3 Seller-Side Health: Churn, Acquisition, Listing Quality

**Seller cohort definitions:**
- **New seller:** first month they appear in `order_items`
- **Active seller:** sold ≥1 item that month
- **Churned seller:** was active in previous month, not active this month
- **Churn rate:** churned sellers / active sellers in prior month

**Listing quality proxy:** avg review score + fulfillment rate (delivered / total orders).
"""),

        code("""\
# Build monthly seller activity table
seller_months = (base.groupby(['seller_id','year_month'])
                 .agg(orders=('order_id','nunique'), gmv=('price','sum'))
                 .reset_index())
seller_months['month'] = seller_months['year_month'].dt.to_timestamp()

# First active month per seller
seller_first = seller_months.groupby('seller_id')['year_month'].min().reset_index()
seller_first.columns = ['seller_id','first_month']
seller_months = seller_months.merge(seller_first, on='seller_id')

# New sellers per month
new_sellers = (seller_months[seller_months['year_month'] == seller_months['first_month']]
               .groupby('month').size().reset_index(name='new_sellers'))

# Churn: present in month t-1, absent in month t
all_periods = sorted(seller_months['year_month'].unique())
churn_rows = []
for i in range(1, len(all_periods)):
    prev, curr = all_periods[i-1], all_periods[i]
    prev_sellers = set(seller_months[seller_months['year_month']==prev]['seller_id'])
    curr_sellers = set(seller_months[seller_months['year_month']==curr]['seller_id'])
    churned = len(prev_sellers - curr_sellers)
    churn_rate = churned / len(prev_sellers) if prev_sellers else 0
    churn_rows.append({'month': curr.to_timestamp(), 'churned': churned,
                       'churn_rate': churn_rate, 'active': len(curr_sellers)})

churn_df = pd.DataFrame(churn_rows).iloc[:-1]  # trim last partial month
new_sellers = new_sellers[(new_sellers['month'] > new_sellers['month'].min()) &
                           (new_sellers['month'] < new_sellers['month'].max())]

print("Seller churn stats:")
print(churn_df[['month','active','churned','churn_rate']].to_string(index=False))
"""),

        code("""\
seller_quality = (base[base['order_status']=='delivered']
    .merge(reviews[['order_id','review_score']], on='order_id', how='left')
    .groupby('seller_id')
    .agg(
        total_orders   = ('order_id','nunique'),
        fulfilled      = ('order_status', lambda x: (x=='delivered').sum()),
        avg_review     = ('review_score','mean'),
    ).reset_index())
seller_quality['fulfillment_rate'] = seller_quality['fulfilled'] / seller_quality['total_orders']
# Quality score = simple average of normalized review (0-1) and fulfillment rate
seller_quality['quality_score'] = (
    (seller_quality['avg_review'] / 5) * 0.5 +
     seller_quality['fulfillment_rate'] * 0.5)

print(f"Median seller quality score: {seller_quality['quality_score'].median():.3f}")
print(seller_quality[['avg_review','fulfillment_rate','quality_score']].describe().round(3))
"""),

        code("""\
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# New vs churned sellers
churn_new = churn_df.merge(new_sellers, on='month', how='left').fillna(0)
x = range(len(churn_new))
axes[0].bar(x, churn_new['new_sellers'], label='New Sellers', color='#4CAF50', alpha=0.8)
axes[0].bar(x, -churn_new['churned'], label='Churned Sellers', color='#f44336', alpha=0.8)
axes[0].set_xticks(list(x)[::2])
axes[0].set_xticklabels([d.strftime('%b %y') for d in churn_new['month'].iloc[::2]], rotation=45)
axes[0].axhline(0, color='black', linewidth=0.8)
axes[0].set_title('New vs. Churned Sellers per Month', fontsize=12, fontweight='bold')
axes[0].set_ylabel('Seller Count')
axes[0].legend()

# Monthly churn rate
axes[1].plot(churn_df['month'], churn_df['churn_rate'] * 100,
             color='#f44336', linewidth=2, marker='o')
axes[1].axhline(churn_df['churn_rate'].mean() * 100, linestyle='--', color='gray',
                label=f"Avg: {churn_df['churn_rate'].mean()*100:.1f}%")
axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=45)
axes[1].set_title('Monthly Seller Churn Rate', fontsize=12, fontweight='bold')
axes[1].set_ylabel('Churn Rate (%)')
axes[1].legend()

# Seller quality distribution
axes[2].hist(seller_quality['quality_score'].dropna(), bins=30,
             color='steelblue', alpha=0.75, edgecolor='white')
axes[2].axvline(seller_quality['quality_score'].median(), color='red',
                linestyle='--', label=f"Median: {seller_quality['quality_score'].median():.2f}")
axes[2].set_title('Seller Quality Score Distribution\\n(0.5×review + 0.5×fulfillment)',
                  fontsize=12, fontweight='bold')
axes[2].set_xlabel('Quality Score (0–1)')
axes[2].set_ylabel('Number of Sellers')
axes[2].legend()

plt.tight_layout()
plt.savefig('../images/seller_health.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## 2.4 Buyer-Side Health: Cohort Retention

**Buyer cohort:** group customers by the month of their **first** purchase.
**Retention in month N:** % of that cohort who placed another order N months later.

This is the single most important demand-side metric: it tells you whether
the product is retaining buyers or is purely acquisition-driven.
"""),

        code("""\
cust_orders = (orders[orders['order_status']=='delivered']
               .merge(customers[['customer_id','customer_unique_id']], on='customer_id'))
cust_orders['order_month'] = cust_orders['order_purchase_timestamp'].dt.to_period('M')

# First purchase month per unique customer
first_purchase = (cust_orders.groupby('customer_unique_id')['order_month']
                  .min().reset_index(name='cohort_month'))
cust_orders = cust_orders.merge(first_purchase, on='customer_unique_id')

cust_orders['months_since_first'] = (
    cust_orders['order_month'] - cust_orders['cohort_month']).apply(lambda x: x.n)

# Build cohort retention matrix
cohort_size = (cust_orders[cust_orders['months_since_first']==0]
               .groupby('cohort_month')['customer_unique_id'].nunique())
cohort_data = (cust_orders.groupby(['cohort_month','months_since_first'])
               ['customer_unique_id'].nunique().reset_index())

retention_pivot = cohort_data.pivot(
    index='cohort_month', columns='months_since_first', values='customer_unique_id')
retention_rate = retention_pivot.divide(cohort_size, axis=0)

# Keep cohorts with enough data (at least 6 months of history)
retention_rate = retention_rate.iloc[:, :13]  # 0–12 months
recent_cohorts = retention_rate.iloc[1:-6]    # trim incomplete cohorts at edges
print(f"Cohort table shape: {recent_cohorts.shape}")
print(f"Month-1 average retention: {recent_cohorts[1].mean()*100:.2f}%")
print(f"Month-6 average retention: {recent_cohorts.get(6, pd.Series([0])).mean()*100:.2f}%")
"""),

        code("""\
fig, ax = plt.subplots(figsize=(14, 8))
mask = recent_cohorts.isnull()
labels = recent_cohorts.applymap(lambda x: f'{x:.0%}' if pd.notna(x) else '')
sns.heatmap(recent_cohorts.fillna(0), ax=ax, cmap='YlGn',
            vmin=0, vmax=0.15,
            annot=labels, fmt='', annot_kws={'size': 8},
            linewidths=0.3, mask=mask)
ax.set_title('Buyer Cohort Retention Matrix\\n(% of cohort who re-ordered)',
             fontsize=14, fontweight='bold')
ax.set_xlabel('Months Since First Purchase')
ax.set_ylabel('First Purchase Cohort')
ax.set_yticklabels([str(c) for c in recent_cohorts.index], rotation=0, fontsize=9)
plt.tight_layout()
plt.savefig('../images/cohort_retention.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## 2.5 Matching Efficiency: Orders per Active Seller per Category

**Matching efficiency** quantifies how well the supply side is meeting demand.
For each category, we track the monthly trend of orders per active seller.
A sudden drop signals sellers leaving without demand following — supply-side churn.
A sudden spike means demand surged but seller count didn't grow to match.
"""),

        code("""\
matching = (base[base['order_status']=='delivered']
            .groupby(['month','category'])
            .agg(orders=('order_id','nunique'), sellers=('seller_id','nunique'))
            .reset_index())
matching['orders_per_seller'] = matching['orders'] / matching['sellers']

# Filter to top 10 categories with most total orders
top10 = (base[base['order_status']=='delivered']
         .groupby('category')['order_id'].nunique()
         .nlargest(10).index.tolist())

matching_top = matching[
    (matching['category'].isin(top10)) &
    (matching['month'] > matching['month'].min()) &
    (matching['month'] < matching['month'].max())]

# Final comparison bar chart (avg orders/seller)
avg_match = (matching_top.groupby('category')['orders_per_seller']
             .mean().sort_values(ascending=True))

fig, axes = plt.subplots(1, 2, figsize=(17, 6))

# Left: time series
colors = plt.cm.tab10.colors
for i, cat in enumerate(top10):
    sub = matching_top[matching_top['category']==cat]
    axes[0].plot(sub['month'], sub['orders_per_seller'],
                 linewidth=1.5, marker='.', alpha=0.8, color=colors[i], label=cat)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
axes[0].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45)
axes[0].set_title('Matching Efficiency Over Time (Orders/Seller)',
                  fontsize=12, fontweight='bold')
axes[0].set_xlabel('Month')
axes[0].set_ylabel('Orders per Active Seller')
axes[0].legend(fontsize=8, loc='upper left')

# Right: ranking bar
axes[1].barh(avg_match.index, avg_match.values, color='steelblue', alpha=0.8)
axes[1].axvline(avg_match.mean(), linestyle='--', color='red',
                label=f'Average: {avg_match.mean():.1f}')
axes[1].set_title('Avg Orders per Active Seller (All-Time)',
                  fontsize=12, fontweight='bold')
axes[1].set_xlabel('Avg Orders per Seller')
axes[1].legend()

plt.tight_layout()
plt.savefig('../images/matching_efficiency.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## Layer 2 Drill-Down Summary

| Drill-Down | Key Finding Signal | Next Action |
|------------|-------------------|-------------|
| GMV by Category | Which category is falling? | → Investigate seller supply in that category |
| GMV by Region | Which region is declining? | → Check logistics performance in that region |
| Seller Churn | Rising churn rate? | → Trigger seller retention campaign |
| New Seller Acq | Slowing inflow? | → Boost seller recruitment spend |
| Cohort Retention | Low Month-1 return rate? | → Buyer re-engagement program |
| Matching Efficiency | Orders/seller dropping? | → Balance supply (reduce) or stimulate demand |

→ **Use `03_forecasting.ipynb` to project where these metrics are headed.**
"""),

    ]
    return nb


# ─────────────────────────────────────────────────────────────────────────────
# NOTEBOOK 3 — Layer 3: Prediction & Forecasting
# ─────────────────────────────────────────────────────────────────────────────
def build_nb3():
    nb = nbf.v4.new_notebook(metadata=make_meta())
    nb.cells = [

        md("""# Layer 3: Prediction & Forecasting (앞으로 어떻게 될까?)

## Why This Analysis Matters
Reactive dashboards tell you what happened. Forecasting tells you what to prepare for.
For a marketplace operations team, three forward-looking questions dominate:

1. **GMV forecast:** What is next quarter's revenue likely to be?
2. **Seller churn risk:** Which sellers are about to go inactive?
3. **Anomaly detection:** Which current metrics are outside normal bounds?

This notebook addresses all three using Prophet, rule-based scoring, and rolling z-scores.
"""),

        code("""\
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams['figure.dpi'] = 120

orders      = pd.read_csv('../data/olist_orders_dataset.csv',
    parse_dates=['order_purchase_timestamp','order_delivered_customer_date'])
order_items = pd.read_csv('../data/olist_order_items_dataset.csv')
customers   = pd.read_csv('../data/olist_customers_dataset.csv')
reviews     = pd.read_csv('../data/olist_order_reviews_dataset.csv')
products    = pd.read_csv('../data/olist_products_dataset.csv')
category_trans = pd.read_csv('../data/product_category_name_translation.csv')

orders['month'] = orders['order_purchase_timestamp'].dt.to_period('M').dt.to_timestamp()
print(f"Date range: {orders['order_purchase_timestamp'].min().date()} "
      f"to {orders['order_purchase_timestamp'].max().date()}")
"""),

        md("""## 3.1 GMV Forecast with Facebook Prophet

Prophet is well-suited for business time series because it handles:
- Trend changes (e.g., platform growth inflections)
- Weekly / yearly seasonality
- Holiday effects (optional)

We train on observed monthly GMV and forecast 6 months ahead.
"""),

        code("""\
from prophet import Prophet

# Build training data
oi = orders.merge(order_items[['order_id','price']], on='order_id')
gmv = (oi[oi['order_status']=='delivered']
       .groupby('month')['price'].sum()
       .reset_index(name='y'))
gmv = gmv.rename(columns={'month':'ds'})
gmv = gmv.iloc[1:-1].copy()  # trim partial months

print(f"Training on {len(gmv)} monthly data points")
print(gmv.tail(6).to_string(index=False))
"""),

        code("""\
model = Prophet(
    yearly_seasonality=False,  # only ~2 years of data, not enough for yearly
    weekly_seasonality=False,
    daily_seasonality=False,
    changepoint_prior_scale=0.15,  # allow moderate flexibility
    seasonality_mode='multiplicative',
    interval_width=0.90
)
model.fit(gmv)

# Forecast 6 months into the future
future = model.make_future_dataframe(periods=6, freq='MS')
forecast = model.predict(future)

fig, ax = plt.subplots(figsize=(14, 6))
ax.fill_between(forecast['ds'], forecast['yhat_lower'], forecast['yhat_upper'],
                alpha=0.2, color='royalblue', label='90% Confidence Interval')
ax.plot(forecast['ds'], forecast['yhat'],
        color='royalblue', linewidth=2, label='Forecast')
ax.scatter(gmv['ds'], gmv['y'],
           color='navy', zorder=5, s=50, label='Actual GMV')

# Mark the forecast start
last_date = gmv['ds'].max()
ax.axvline(last_date, color='red', linestyle='--', linewidth=1.2, label='Forecast Start')

ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.xticks(rotation=45)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'R${x/1e6:.1f}M'))
ax.set_title('GMV Forecast — Prophet (6-Month Horizon)', fontsize=15, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('GMV (BRL)')
ax.legend()
plt.tight_layout()
plt.savefig('../images/gmv_forecast.png', dpi=150, bbox_inches='tight')
plt.show()

# Print forecast numbers
print("\\nForecast for next 6 months:")
future_rows = forecast[forecast['ds'] > last_date][['ds','yhat','yhat_lower','yhat_upper']]
future_rows.columns = ['Month','Forecast','Lower (90%)','Upper (90%)']
for col in ['Forecast','Lower (90%)','Upper (90%)']:
    future_rows[col] = future_rows[col].apply(lambda x: f'R${x:,.0f}')
print(future_rows.to_string(index=False))
"""),

        md("""## 3.2 Seller Churn Risk Prediction (Rule-Based)

We flag sellers as "at risk" using a simple but effective rule-based approach:

**At-risk seller criteria (any 2 of 3):**
1. Order volume in the last 30 days is ≤50% of their historical monthly average
2. No sales in the last 45 days
3. Average review score < 3.5

This rule-based approach is explainable, easy to operationalize, and appropriate
given the dataset's time range. A more advanced model (logistic regression, XGBoost)
would require labelled churn outcomes from future data.
"""),

        code("""\
base = (orders.merge(order_items[['order_id','price','seller_id']], on='order_id')
              .merge(reviews[['order_id','review_score']], on='order_id', how='left'))

cutoff = base['order_purchase_timestamp'].max()
window_30  = cutoff - pd.Timedelta(days=30)
window_45  = cutoff - pd.Timedelta(days=45)
window_hist = cutoff - pd.Timedelta(days=180)  # 6-month historical baseline

# Per-seller stats
seller_stats = base.groupby('seller_id').apply(lambda g: pd.Series({
    'last_order_date':   g['order_purchase_timestamp'].max(),
    'orders_last_30d':   (g['order_purchase_timestamp'] >= window_30).sum(),
    'orders_hist_6m':    (g['order_purchase_timestamp'] >= window_hist).sum(),
    'avg_review':        g['review_score'].mean(),
    'total_orders':      len(g),
})).reset_index()

seller_stats['avg_monthly_hist'] = seller_stats['orders_hist_6m'] / 6
seller_stats['days_since_last']  = (cutoff - seller_stats['last_order_date']).dt.days

# Risk flags
seller_stats['flag_volume_drop'] = (
    (seller_stats['avg_monthly_hist'] > 0) &
    (seller_stats['orders_last_30d'] <= seller_stats['avg_monthly_hist'] * 0.5))
seller_stats['flag_inactive'] = seller_stats['days_since_last'] >= 45
seller_stats['flag_low_review'] = seller_stats['avg_review'] < 3.5

seller_stats['risk_flags'] = (seller_stats['flag_volume_drop'].astype(int) +
                               seller_stats['flag_inactive'].astype(int) +
                               seller_stats['flag_low_review'].astype(int))
seller_stats['churn_risk'] = seller_stats['risk_flags'].map(
    {0:'Low', 1:'Medium', 2:'High', 3:'Critical'})

print("Seller churn risk distribution:")
print(seller_stats['churn_risk'].value_counts().to_string())
print(f"\\nAt-risk sellers (High+Critical): "
      f"{(seller_stats['risk_flags'] >= 2).sum():,} "
      f"({(seller_stats['risk_flags'] >= 2).mean()*100:.1f}% of active sellers)")
"""),

        code("""\
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Risk distribution
risk_counts = seller_stats['churn_risk'].value_counts()
risk_order = ['Low','Medium','High','Critical']
risk_colors = {'Low':'#4CAF50','Medium':'#FFC107','High':'#FF5722','Critical':'#B71C1C'}
bars = axes[0].bar(
    [r for r in risk_order if r in risk_counts.index],
    [risk_counts.get(r, 0) for r in risk_order],
    color=[risk_colors[r] for r in risk_order if r in risk_counts.index],
    edgecolor='white', alpha=0.85)
for bar in bars:
    axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                 str(int(bar.get_height())), ha='center', va='bottom', fontweight='bold')
axes[0].set_title('Seller Churn Risk Distribution', fontsize=13, fontweight='bold')
axes[0].set_xlabel('Risk Level')
axes[0].set_ylabel('Number of Sellers')

# Volume drop vs avg review (scatter coloured by risk)
at_risk = seller_stats[seller_stats['risk_flags'] >= 2].copy()
not_risk = seller_stats[seller_stats['risk_flags'] < 2].copy()

axes[1].scatter(not_risk['avg_monthly_hist'], not_risk['avg_review'],
                color='#90CAF9', alpha=0.4, s=20, label='Low/Medium Risk')
axes[1].scatter(at_risk['avg_monthly_hist'], at_risk['avg_review'],
                color='red', alpha=0.6, s=30, label='High/Critical Risk')
axes[1].axhline(3.5, color='orange', linestyle='--', linewidth=1, label='Review Threshold (3.5)')
axes[1].set_xlim(left=0)
axes[1].set_title('At-Risk Sellers: Volume vs Review Score',
                  fontsize=13, fontweight='bold')
axes[1].set_xlabel('Avg Monthly Orders (6-Month Hist.)')
axes[1].set_ylabel('Avg Review Score')
axes[1].legend(fontsize=9)

plt.tight_layout()
plt.savefig('../images/seller_churn_risk.png', dpi=150, bbox_inches='tight')
plt.show()

# Show top 10 highest-risk sellers
high_risk = (seller_stats[seller_stats['risk_flags'] >= 2]
             .sort_values('risk_flags', ascending=False)
             .head(10)[['seller_id','days_since_last','orders_last_30d',
                         'avg_monthly_hist','avg_review','churn_risk']]
             .round(2))
print("\\nTop 10 At-Risk Sellers:")
print(high_risk.to_string(index=False))
"""),

        md("""## 3.3 Anomaly Detection Dashboard — Rolling Z-Score

We apply rolling z-score anomaly detection across four key metrics simultaneously.
This is the same method used in Layer 1 for GMV, now extended to:
- Monthly active buyers
- Monthly active sellers
- Completion rate
- Avg review score

The purpose is to give an on-call team a single view of which metrics are currently outside normal operating range.
"""),

        code("""\
# Build all four monthly metrics
orders_cust = orders.merge(
    customers[['customer_id','customer_unique_id']], on='customer_id')
active_buyers = (orders_cust.groupby('month')['customer_unique_id']
                 .nunique().reset_index(name='active_buyers'))

orders_sell = orders.merge(order_items[['order_id','seller_id']], on='order_id')
active_sellers = (orders_sell.groupby('month')['seller_id']
                  .nunique().reset_index(name='active_sellers'))

orders_oi = orders.merge(order_items[['order_id','price']], on='order_id')
gmv_m = (orders_oi[orders_oi['order_status']=='delivered']
         .groupby('month')['price'].sum().reset_index(name='gmv'))

comp = (orders.groupby('month')
        .apply(lambda x: (x['order_status']=='delivered').sum() / len(x))
        .reset_index(name='completion_rate'))

rev_m = (orders.merge(reviews[['order_id','review_score']], on='order_id', how='left')
         .groupby('month')['review_score'].mean().reset_index(name='avg_review'))

metrics_df = (gmv_m.merge(active_buyers, on='month')
                    .merge(active_sellers, on='month')
                    .merge(comp, on='month')
                    .merge(rev_m, on='month')
                    .iloc[1:-1].reset_index(drop=True))

# Compute rolling z-score for each metric
WINDOW = 4
metric_cols = ['gmv','active_buyers','active_sellers','completion_rate','avg_review']
metric_labels = ['GMV','Active Buyers','Active Sellers','Completion Rate','Avg Review']

for col in metric_cols:
    metrics_df[f'{col}_roll_mean'] = metrics_df[col].rolling(WINDOW, center=True, min_periods=2).mean()
    metrics_df[f'{col}_roll_std']  = metrics_df[col].rolling(WINDOW, center=True, min_periods=2).std()
    metrics_df[f'{col}_z']         = ((metrics_df[col] - metrics_df[f'{col}_roll_mean'])
                                       / metrics_df[f'{col}_roll_std'])
    metrics_df[f'{col}_anomaly']   = metrics_df[f'{col}_z'].abs() > 2

print("Anomaly detections per metric:")
for col, label in zip(metric_cols, metric_labels):
    n = metrics_df[f'{col}_anomaly'].sum()
    print(f"  {label}: {n} anomalous months")
"""),

        code("""\
fig, axes = plt.subplots(len(metric_cols), 1, figsize=(14, 18), sharex=True)

for i, (col, label) in enumerate(zip(metric_cols, metric_labels)):
    ax = axes[i]
    ax.plot(metrics_df['month'], metrics_df[f'{col}_z'],
            color='steelblue', linewidth=1.8, label='Z-Score')
    ax.fill_between(metrics_df['month'], -2, 2, alpha=0.1, color='green',
                    label='Normal Band (±2σ)')
    ax.axhline( 2, color='orange', linestyle='--', linewidth=1)
    ax.axhline(-2, color='orange', linestyle='--', linewidth=1)
    ax.axhline( 0, color='gray', linestyle='-', linewidth=0.5)

    anomalies = metrics_df[metrics_df[f'{col}_anomaly']]
    ax.scatter(anomalies['month'], anomalies[f'{col}_z'],
               color='red', zorder=5, s=80, marker='X', label='Anomaly')

    ax.set_ylabel('Z-Score', fontsize=10)
    ax.set_title(f'{label} — Rolling Z-Score (window={WINDOW})',
                 fontsize=11, fontweight='bold')
    if i == 0:
        ax.legend(loc='upper left', fontsize=9)

axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45)

plt.suptitle('Marketplace Anomaly Detection Dashboard\\n(Rolling Z-Score across Key Metrics)',
             fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig('../images/anomaly_dashboard.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## Layer 3 Forecasting Summary

| Output | Method | Key Output |
|--------|--------|-----------|
| GMV Forecast | Facebook Prophet | 6-month projection with 90% CI |
| Seller Churn Risk | Rule-based (3-flag scoring) | High/Critical risk seller list |
| Anomaly Dashboard | Rolling z-score (window=4) | All metrics, alert at \\|z\\| > 2 |

**Operational workflow:**
1. Run anomaly dashboard weekly — if any metric has |z| > 2, escalate
2. Run seller churn risk monthly — export High/Critical list for retention team
3. Update GMV forecast quarterly — adjust targets if lower bound trends down

→ **Use `04_two_sided_market.ipynb` to understand cross-side effects.**
"""),

    ]
    return nb


# ─────────────────────────────────────────────────────────────────────────────
# NOTEBOOK 4 — Layer 4: Two-Sided Market Analysis
# ─────────────────────────────────────────────────────────────────────────────
def build_nb4():
    nb = nbf.v4.new_notebook(metadata=make_meta())
    nb.cells = [

        md("""# Layer 4: Two-Sided Market Analysis (양면 시장)

## Why This Analysis Matters
A marketplace is not a store — it is a platform connecting two sides.
Changes on one side propagate to the other through **cross-side network effects**:

- More sellers → more selection → higher buyer conversion
- Fewer sellers → supply gap → buyers leave (demand erosion)
- New (inexperienced) sellers → lower review scores → buyer churn
- Dense seller supply → price competition → higher buyer value

This notebook quantifies these cross-side dynamics using the Olist data.

**Three analyses:**
1. Seller count changes → buyer conversion rate (completion rate proxy)
2. New seller entry → effect on price and review quality
3. Cross-side network effect proxy: seller density vs. buyer retention by category
"""),

        code("""\
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams['figure.dpi'] = 120

orders        = pd.read_csv('../data/olist_orders_dataset.csv',
    parse_dates=['order_purchase_timestamp','order_delivered_customer_date'])
order_items   = pd.read_csv('../data/olist_order_items_dataset.csv')
customers     = pd.read_csv('../data/olist_customers_dataset.csv')
reviews       = pd.read_csv('../data/olist_order_reviews_dataset.csv')
products      = pd.read_csv('../data/olist_products_dataset.csv')
category_trans= pd.read_csv('../data/product_category_name_translation.csv')

orders['month'] = orders['order_purchase_timestamp'].dt.to_period('M').dt.to_timestamp()

items_cat = (order_items
    .merge(products[['product_id','product_category_name']], on='product_id', how='left')
    .merge(category_trans, on='product_category_name', how='left'))
items_cat['category'] = (items_cat['product_category_name_english']
                         .fillna(items_cat['product_category_name']))

base = (orders
    .merge(order_items[['order_id','price','seller_id']], on='order_id')
    .merge(customers[['customer_id','customer_unique_id','customer_state']], on='customer_id')
    .merge(items_cat[['order_id','category']].drop_duplicates(), on='order_id', how='left'))

print(f"Base table: {len(base):,} rows across {base['month'].nunique()} months")
"""),

        md("""## 4.1 Seller Count Changes → Buyer Completion Rate

**Hypothesis:** In months where active seller count drops (supply shock),
the buyer completion rate (orders delivered / orders placed) also drops
because demand finds less available supply, leading to more cancellations
and unmet orders.

We test this by computing the Pearson correlation between MoM seller count change
and MoM completion rate change, and visualising the relationship.
"""),

        code("""\
# Monthly active sellers
orders_sell = orders.merge(order_items[['order_id','seller_id']], on='order_id')
active_sellers = (orders_sell.groupby('month')['seller_id']
                  .nunique().reset_index(name='active_sellers'))

# Monthly completion rate
completion = (orders.groupby('month')
              .apply(lambda x: (x['order_status']=='delivered').sum() / len(x))
              .reset_index(name='completion_rate'))

cross = (active_sellers.merge(completion, on='month')
                       .iloc[1:-1].reset_index(drop=True))

cross['seller_mom_chg']     = cross['active_sellers'].pct_change() * 100
cross['completion_mom_chg'] = cross['completion_rate'].pct_change() * 100
cross_clean = cross.dropna()

r, p = stats.pearsonr(cross_clean['seller_mom_chg'], cross_clean['completion_mom_chg'])
print(f"Pearson r = {r:.3f},  p-value = {p:.4f}")
print(f"Interpretation: {'Significant' if p < 0.05 else 'Not significant'} at 95% confidence")
"""),

        code("""\
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Left: scatter with regression line
m, b = np.polyfit(cross_clean['seller_mom_chg'],
                   cross_clean['completion_mom_chg'], 1)
x_line = np.linspace(cross_clean['seller_mom_chg'].min(),
                      cross_clean['seller_mom_chg'].max(), 100)
axes[0].scatter(cross_clean['seller_mom_chg'], cross_clean['completion_mom_chg'],
                color='steelblue', alpha=0.7, s=60)
axes[0].plot(x_line, m * x_line + b, color='red', linewidth=2,
             label=f'OLS fit (r={r:.2f}, p={p:.3f})')
axes[0].axhline(0, color='gray', linewidth=0.8, linestyle='--')
axes[0].axvline(0, color='gray', linewidth=0.8, linestyle='--')
axes[0].set_title('Seller Count Change → Completion Rate Change\\n(Monthly % Change)',
                  fontsize=12, fontweight='bold')
axes[0].set_xlabel('MoM Active Seller Change (%)')
axes[0].set_ylabel('MoM Completion Rate Change (%)')
axes[0].legend()

# Right: time series overlay
ax_r = axes[1]
ax_r2 = ax_r.twinx()

ax_r.plot(cross['month'], cross['active_sellers'],
          color='#FF5722', linewidth=2, marker='o', label='Active Sellers')
ax_r.set_ylabel('Active Sellers', color='#FF5722')
ax_r.tick_params(axis='y', colors='#FF5722')

ax_r2.plot(cross['month'], cross['completion_rate'] * 100,
           color='#2196F3', linewidth=2, marker='s', label='Completion Rate')
ax_r2.set_ylabel('Completion Rate (%)', color='#2196F3')
ax_r2.tick_params(axis='y', colors='#2196F3')

ax_r.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax_r.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.setp(ax_r.xaxis.get_majorticklabels(), rotation=45)
ax_r.set_title('Active Sellers vs. Completion Rate Over Time',
               fontsize=12, fontweight='bold')

lines1, labels1 = ax_r.get_legend_handles_labels()
lines2, labels2 = ax_r2.get_legend_handles_labels()
ax_r.legend(lines1 + lines2, labels1 + labels2, loc='lower right', fontsize=9)

plt.tight_layout()
plt.savefig('../images/seller_count_vs_conversion.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## 4.2 New Seller Entry → Effect on Price & Review Quality

**Hypothesis:** When new, inexperienced sellers enter the market:
- **Prices drop** (competition for buyers via lower prices)
- **Review scores drop** (new sellers have worse service quality)

We test this by comparing "new seller cohort months" (months with high new-seller
entry) against incumbent-seller metrics on price and review score.
"""),

        code("""\
# Tag each transaction by seller cohort: new vs. established
first_sale = (base.groupby('seller_id')['order_purchase_timestamp']
              .min().reset_index(name='first_sale_date'))
base_cohort = base.merge(first_sale, on='seller_id')

# "New seller" = seller whose first sale was within last 60 days of the order
base_cohort['seller_tenure_days'] = (
    (base_cohort['order_purchase_timestamp'] - base_cohort['first_sale_date']).dt.days)
base_cohort['seller_type'] = np.where(
    base_cohort['seller_tenure_days'] <= 60, 'New Seller (<60d)', 'Established Seller')

# Attach review scores
cohort_rev = base_cohort.merge(reviews[['order_id','review_score']], on='order_id', how='left')

monthly_cohort = (cohort_rev[cohort_rev['order_status']=='delivered']
    .groupby(['month','seller_type'])
    .agg(avg_price=('price','mean'), avg_review=('review_score','mean'),
         order_count=('order_id','nunique'))
    .reset_index())

monthly_cohort = monthly_cohort[
    (monthly_cohort['month'] > monthly_cohort['month'].min()) &
    (monthly_cohort['month'] < monthly_cohort['month'].max())]

print("Price and review comparison by seller type:")
print(monthly_cohort.groupby('seller_type')[['avg_price','avg_review']].mean().round(3))
"""),

        code("""\
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

for seller_type, color, style in [
        ('New Seller (<60d)', '#FF5722', '-'),
        ('Established Seller', '#2196F3', '--')]:
    sub = monthly_cohort[monthly_cohort['seller_type']==seller_type]
    axes[0].plot(sub['month'], sub['avg_price'], color=color, linestyle=style,
                 linewidth=2, marker='.', label=seller_type)
    axes[1].plot(sub['month'], sub['avg_review'], color=color, linestyle=style,
                 linewidth=2, marker='.', label=seller_type)

for ax, title, ylabel in zip(axes,
    ['New vs. Established Sellers: Avg Item Price', 'New vs. Established Sellers: Avg Review Score'],
    ['Average Price (BRL)', 'Average Review Score (1–5)']):
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel('Month')
    ax.set_ylabel(ylabel)
    ax.legend()

axes[1].axhline(4.0, color='orange', linestyle=':', linewidth=1.2,
                label='Target Score (4.0)')
axes[1].legend()

plt.tight_layout()
plt.savefig('../images/new_seller_effect.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## 4.3 Cross-Side Network Effect: Seller Density → Buyer Retention

**Hypothesis:** Categories with higher seller density (more sellers competing)
have better buyer retention because buyers find better options and return.

**Method:** For each category, compute:
- **Seller density** = avg number of active sellers per month
- **Buyer retention** = % of buyers in a category who returned to buy again (from any category)

Then test the correlation. A positive correlation confirms a supply-side network effect.
"""),

        code("""\
# Per-category seller density
cat_sellers = (base[base['order_status']=='delivered']
    .groupby(['month','category'])['seller_id']
    .nunique().reset_index(name='n_sellers'))
cat_density = cat_sellers.groupby('category')['n_sellers'].mean().reset_index(name='avg_sellers')

# Per-category buyer retention
# A buyer "retained" in a category if they made ≥2 orders in that category
cat_buyer_orders = (base[base['order_status']=='delivered']
    .groupby(['category','customer_unique_id'])['order_id']
    .nunique().reset_index(name='orders_in_cat'))

cat_retention = (cat_buyer_orders.groupby('category')
    .apply(lambda g: (g['orders_in_cat'] > 1).sum() / len(g))
    .reset_index(name='buyer_retention_rate'))

cat_combined = cat_density.merge(cat_retention, on='category')
# Filter to categories with at least 200 unique buyers for statistical significance
cat_min_buyers = (cat_buyer_orders.groupby('category').size()
                  .reset_index(name='n_buyers'))
cat_combined = cat_combined.merge(cat_min_buyers, on='category')
cat_combined = cat_combined[cat_combined['n_buyers'] >= 200]

r2, p2 = stats.pearsonr(cat_combined['avg_sellers'], cat_combined['buyer_retention_rate'])
print(f"Pearson r = {r2:.3f}, p-value = {p2:.4f}")
print(f"Categories analyzed: {len(cat_combined)}")
print(cat_combined.sort_values('buyer_retention_rate', ascending=False).head(10)
      [['category','avg_sellers','buyer_retention_rate','n_buyers']].to_string(index=False))
"""),

        code("""\
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Left: scatter — seller density vs buyer retention
sc = axes[0].scatter(cat_combined['avg_sellers'], cat_combined['buyer_retention_rate'] * 100,
                     c=cat_combined['n_buyers'], cmap='viridis', s=80, alpha=0.8)
plt.colorbar(sc, ax=axes[0], label='Total Unique Buyers')

m2, b2 = np.polyfit(cat_combined['avg_sellers'],
                     cat_combined['buyer_retention_rate'] * 100, 1)
x2 = np.linspace(cat_combined['avg_sellers'].min(), cat_combined['avg_sellers'].max(), 100)
axes[0].plot(x2, m2*x2 + b2, color='red', linewidth=2,
             label=f'OLS fit (r={r2:.2f}, p={p2:.3f})')

for _, row in cat_combined.nlargest(5, 'n_buyers').iterrows():
    axes[0].annotate(row['category'][:18], (row['avg_sellers'], row['buyer_retention_rate']*100),
                     fontsize=7, ha='left', va='bottom', alpha=0.7)

axes[0].set_title('Seller Density vs. Buyer Retention Rate\\n(Cross-Side Network Effect)',
                  fontsize=12, fontweight='bold')
axes[0].set_xlabel('Avg Active Sellers per Month (Density)')
axes[0].set_ylabel('Buyer Retention Rate (%)')
axes[0].legend(fontsize=9)

# Right: Top 15 categories by retention
top_ret = cat_combined.nlargest(15, 'buyer_retention_rate')
axes[1].barh(top_ret['category'], top_ret['buyer_retention_rate'] * 100,
             color='steelblue', alpha=0.8)
axes[1].axvline(cat_combined['buyer_retention_rate'].mean() * 100,
                color='red', linestyle='--',
                label=f"Avg: {cat_combined['buyer_retention_rate'].mean()*100:.1f}%")
axes[1].set_title('Top 15 Categories by Buyer Retention Rate',
                  fontsize=12, fontweight='bold')
axes[1].set_xlabel('Buyer Retention Rate (%)')
axes[1].legend(fontsize=9)

plt.tight_layout()
plt.savefig('../images/network_effects.png', dpi=150, bbox_inches='tight')
plt.show()
"""),

        md("""## Layer 4 Two-Sided Market Summary

| Finding | Direction | Strength | Interpretation |
|---------|-----------|----------|---------------|
| Seller count → completion rate | Positive | r = see output | Supply shocks hurt transaction success |
| New sellers → avg price | Negative | See plot | New entrants compete on price |
| New sellers → review score | Negative | See plot | New sellers have worse service quality |
| Seller density → buyer retention | Positive | r = see output | More supply drives buyer loyalty |

### Strategic Implications for Korean Marketplace Context
- **Seller acquisition** is not just about GMV — it directly supports buyer retention.
- **New seller onboarding quality** matters: inexperienced sellers drag down review scores
  and may harm buyer trust. → Invest in seller training and listing quality checks.
- **Category-level monitoring** is more actionable than platform-wide metrics:
  a supply gap in one category can drive buyers to competitors entirely.
"""),

    ]
    return nb


# ─────────────────────────────────────────────────────────────────────────────
# Write all notebooks
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    notebooks = {
        'notebooks/01_marketplace_health.ipynb': build_nb1(),
        'notebooks/02_drilldown_analysis.ipynb': build_nb2(),
        'notebooks/03_forecasting.ipynb':        build_nb3(),
        'notebooks/04_two_sided_market.ipynb':   build_nb4(),
    }

    for path, nb in notebooks.items():
        full_path = os.path.join(ROOT, path)
        with open(full_path, 'w') as f:
            nbf.write(nb, f)
        print(f"✓ Written: {path}")

    print("\nAll notebooks generated successfully.")
