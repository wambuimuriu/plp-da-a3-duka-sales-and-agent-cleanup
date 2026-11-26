# PLP Data Analytics · Assignment 3: Duka Sales and Agent Cleanup

Two client engagements from a Nairobi analytics consultancy.

## 1. Engagement summaries

**Duka Electronics (half-year sales review, Jan–Jun 2026).** Exploration of 1,000 orders (seed 2026): inspection, derived columns, branch/product/weekend/month comparisons, Premium online orders for Nairobi and Mombasa, and an Excel cross-check (SUMIFS, XLOOKUP, branch x channel table). The 1,000-order sales file was inspected, extended with `revenue`, `month`, `weekday`, `is_weekend` and `price_band`, and analysed by branch, product, weekday/weekend and month. Findings: Nairobi earns 36.4% of revenue, Laptops earn 57.9% of revenue, weekend orders are as valuable as weekday orders, and April beat June by 24.0%. The 83 Premium online orders from Nairobi and Mombasa (KES 10.2M) are exported to `outputs/premium_online_coast_capital.csv`, and an Excel workbook (SUMIFS, XLOOKUP, branch x channel cross-tab) reconciles to pandas exactly.

**Mobile-money agent network.** The legacy extract of 612 transactions was audited, cleaned, merged with the 20-agent register and summarised by county and week. Eight issue types were found across six data-quality dimensions. The pipeline is reusable (`clean_agent_data()`), and a full Data Quality Report is at the end of `agent_cleanup.ipynb`.

## 2. Regenerate the data and run the notebooks

```bash
pip install -r requirements.txt jupyter
python generate_data.py          # writes duka_sales.csv, agents.csv, agent_transactions.csv
jupyter nbconvert --to notebook --execute --inplace duka_sales_exploration.ipynb
jupyter nbconvert --to notebook --execute --inplace agent_cleanup.ipynb
```

The raw CSVs are not committed; only `outputs/` and `excel/` hold data files.

| File | Purpose |
|---|---|
| `generate_data.py` | Both dataset generators (Duka seed 2026; agents seed 44) |
| `duka_sales_exploration.ipynb` | Engagement 1 analysis |
| `excel/duka_branch_summary.xlsx` | SUMIFS table, XLOOKUP region, PivotTable |
| `outputs/premium_online_coast_capital.csv` | Premium online orders, Nairobi + Mombasa |
| `cleaning_pipeline.py` | `clean_agent_data(txns, agents)` returning `(clean_df, log)` |
| `agent_cleanup.ipynb` | Engagement 2 audit, cleaning, merge, summaries, report |
| `outputs/agent_transactions_clean.csv` | Cleaned, merged transactions |

## 3. Duka Executive Summary

- Duka's 1,000 orders between 1 January and 29 June 2026 produced **KES 71.8M** in revenue (average order KES 71,792), and Nairobi alone delivered **36.4%** of it (KES 26.1M), almost double second-placed Mombasa at 19.5%.
- Laptops generate **57.9%** of revenue (KES 41.5M from 639 units), while Tablets sell more units (691) but earn only KES 19.3M, because a laptop costs KES 65,000 against KES 28,000.
- Weekend orders are **27.7%** of orders (277 orders, KES 19.9M) and are worth almost exactly the same as weekday orders (KES 71,972 vs KES 71,724, a 0.3% difference), so there is no weekend premium or discount.
- Revenue peaked in **April** at KES 13.5M and was lowest in **June** at KES 10.9M, so the best month earned **24.0%** more than the worst.
- The Premium online segment in Nairobi and Mombasa (the coast and capital cities) is **83 orders worth KES 10.2M**, 14.2% of total revenue, and is a ready-made target list for an online campaign.

## 4. Agent data: before and after

| Stage | Rows |
|---|---|
| Raw `agent_transactions.csv` | 612 |
| Duplicate `txn_id` rows removed | 12 |
| **Clean `agent_transactions_clean.csv`** | **600** |

Other cleaning results: 20 missing/invalid amounts imputed and flagged (`amount_imputed`); 40 amounts flagged by IQR (`is_outlier`), including five KES 250,000 values kept for verification; 7 transactions from unknown agent `AG099` kept with county `"Unknown"`.
