# 📦 Olist Marketplace Funnel Analytics
**Optimizing Customer Retention through Logistics Intelligence**

## 🎯 Executive Summary
This project investigates the operational bottlenecks of the Olist Brazilian E-Commerce marketplace. By architecting a local data warehouse and engineering a multi-stage fulfillment funnel, I identified that **carrier transit delays** are the primary driver of the platform's **3.12% retention rate**.

### 💡 Key Findings
* **The Retention Crisis:** Only **3.12%** of customers return for a second purchase.
* **The Fulfillment Bottleneck:** Average delivery takes **12.5 days**; carrier transit accounts for **74%** of that delay.
* **The Satisfaction Threshold:** Data proves a direct correlation—deliveries exceeding **12 days** result in a significant drop in NPS/Review scores.
* **Regional Variance:** A **236% disparity** in delivery speed exists between Southeastern hubs (SP) and Northern regions (RR).

---

## 🛠️ Tech Stack
* **Database:** DuckDB (OLAP-optimized SQL engine)
* **Language:** Python 3.9 (Pandas, Seaborn, Matplotlib)
* **Environment:** VS Code + Jupyter Notebooks
* **Version Control:** Git/GitHub

---

## 🏗️ Project Architecture
I implemented a **Medallion Architecture** to ensure data integrity and performance:
1.  **Bronze Layer:** Raw CSV ingestion into a persistent `olist.db`.
2.  **Silver Layer:** Transformed views and tables cleaning timestamps and joining relational entities.
3.  **Gold Layer:** Business-ready KPIs (GMV, Retention, Lead Time) used for visualization.

---

## 📈 Key Visualizations
### 1. Delivery Time vs. Customer Satisfaction
*(Insert your correlation line chart here)*
> **Insight:** To maintain a 4.5+ star rating, the delivery "Sweet Spot" must be under 11 days.

### 2. Geographic Logistics Latency
*(Insert your bar chart of states here)*
> **Insight:** Northern Brazil requires a decentralized warehouse strategy to combat 20-30 day lead times.

---

## 🚀 Next Steps (Phase 2)
* [ ] **A/B Testing Simulation:** Estimating GMV lift if Northern logistics are optimized.
* [ ] **Seller Tiering:** Automated classification of high-reliability sellers.