"""Reusable cleaning pipeline for the mobile-money agent network extract."""
import numpy as np
import pandas as pd

VALID_TYPES = {"deposit": "Deposit", "withdrawal": "Withdrawal"}


def clean_agent_data(txns, agents):
    """Clean the agent transaction extract and merge it with the agent register.

    Rules applied (each one is logged with the number of rows it touched):
      1. Uniqueness   - drop duplicate ``txn_id`` rows (keep one row per
         transaction, preferring the copy whose agent exists in the register).
      2. Consistency  - strip whitespace / fix case and map ``txn_type`` to
         exactly "Deposit" or "Withdrawal".
      3. Validity     - convert ``amount`` to numeric (text such as "N/A"
         becomes missing) and ``txn_date`` to datetime (mixed "-" and "/"
         separators are normalised); dates are stored as ISO strings.
      4. Outliers     - flag amounts outside the IQR fences (Q1 - 1.5*IQR,
         Q3 + 1.5*IQR) in ``is_outlier``. Outliers are flagged, never removed.
      5. Completeness - impute missing amounts with the median valid,
         non-outlier amount for the same ``txn_type`` and set
         ``amount_imputed`` = True.
      6. Merge        - left join to the register (many-to-one) so that
         transactions from unknown agents are kept; their county is set to
         "Unknown" and they are counted in the log.

    Parameters
    ----------
    txns : pandas.DataFrame
        Raw transactions (txn_id, agent_id, txn_type, amount, txn_date).
    agents : pandas.DataFrame
        Agent register (agent_id, county, onboarded).

    Returns
    -------
    (clean_df, log) : tuple[pandas.DataFrame, pandas.DataFrame]
        The cleaned, merged transactions and a log DataFrame with columns
        step, issue, dimension, column, rows_affected, action.
    """
    log = []

    def record(step, issue, dimension, column, rows, action):
        log.append({"step": step, "issue": issue, "dimension": dimension,
                    "column": column, "rows_affected": int(rows),
                    "action": action})

    df = txns.copy()
    reg = agents.copy()
    reg["onboarded"] = pd.to_datetime(reg["onboarded"], errors="coerce")
    n_start = len(df)

    # 1. Uniqueness -------------------------------------------------------
    df["agent_id"] = df["agent_id"].astype("string").str.strip()
    df["_known"] = df["agent_id"].isin(reg["agent_id"])
    df["_order"] = np.arange(len(df))
    n_dup = df["txn_id"].duplicated().sum()
    df = (df.sort_values(["_known", "_order"], ascending=[False, True])
            .drop_duplicates("txn_id", keep="first")
            .sort_values("_order")
            .drop(columns=["_known", "_order"]))
    record(1, "Duplicate transactions (repeated txn_id)", "Uniqueness",
           "txn_id", n_dup, "Dropped extra copies, kept one row per txn_id")

    # 2. Consistency ------------------------------------------------------
    raw_type = df["txn_type"].astype("string")
    clean_type = raw_type.str.strip().str.lower().map(VALID_TYPES)
    n_fix = (raw_type != clean_type).sum()
    n_bad = clean_type.isna().sum()
    df["txn_type"] = clean_type
    record(2, "Inconsistent txn_type spelling, case or whitespace",
           "Consistency", "txn_type", n_fix,
           'Standardised to "Deposit" / "Withdrawal"')
    if n_bad:
        record(2, "txn_type not recognisable", "Validity", "txn_type", n_bad,
               "Left missing for manual review")

    # 3. Validity and types -----------------------------------------------
    amt_raw = df["amount"]
    amt = pd.to_numeric(amt_raw, errors="coerce")
    n_text = (amt_raw.notna() & amt.isna()).sum()
    n_null = amt_raw.isna().sum()
    df["amount"] = amt
    record(3, 'Non-numeric amount text (e.g. "N/A")', "Validity", "amount",
           n_text, "to_numeric(errors='coerce'); 0 when the CSV reader already "
           "turned \"N/A\" into NaN (counted under Missing amount)")
    record(3, "Missing amount", "Completeness", "amount", n_null,
           "Kept as missing until step 5")

    d_raw = df["txn_date"].astype("string").str.strip()
    n_slash = d_raw.str.contains("/", na=False).sum()
    d = pd.to_datetime(d_raw.str.replace("/", "-", regex=False),
                       format="%Y-%m-%d", errors="coerce")
    record(3, 'Mixed date separator ("/" instead of "-")', "Validity",
           "txn_date", n_slash, "Normalised, parsed as datetime, stored ISO")
    if d.isna().sum():
        record(3, "Unparseable txn_date", "Validity", "txn_date",
               d.isna().sum(), "Left missing for manual review")
    df["txn_date"] = d.dt.strftime("%Y-%m-%d")

    # 4. Outliers (IQR on observed amounts) -------------------------------
    q1, q3 = df["amount"].quantile([0.25, 0.75])
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    df["is_outlier"] = (df["amount"] < low) | (df["amount"] > high)
    record(4, f"Amount outside IQR fences ({low:,.0f} to {high:,.0f})",
           "Accuracy", "amount", df["is_outlier"].sum(),
           "Flagged in is_outlier, values kept")

    # 5. Completeness -----------------------------------------------------
    ok = df.loc[~df["is_outlier"] & df["amount"].notna()]
    med = ok.groupby("txn_type")["amount"].median()
    df["amount_imputed"] = df["amount"].isna()
    fill = df["txn_type"].map(med).fillna(ok["amount"].median())
    df["amount"] = df["amount"].fillna(fill)
    record(5, "Missing/invalid amount imputed", "Completeness", "amount",
           df["amount_imputed"].sum(),
           "Median of valid non-outlier amounts by txn_type; flagged in amount_imputed")

    # 6. Merge ------------------------------------------------------------
    clean = df.merge(reg, on="agent_id", how="left", validate="m:1",
                     indicator=True)
    unknown = clean["_merge"].eq("left_only")
    clean["unknown_agent"] = unknown
    clean["county"] = clean["county"].fillna("Unknown")
    clean = clean.drop(columns="_merge")
    record(6, "Transactions referencing agents not in register",
           "Integrity", "agent_id", unknown.sum(),
           'Kept (left join); county set to "Unknown", flagged unknown_agent')

    assert clean["txn_id"].is_unique and len(clean) == len(df)
    log_df = pd.DataFrame(log)
    log_df.attrs["rows_before"] = n_start
    log_df.attrs["rows_after"] = len(clean)
    return clean.reset_index(drop=True), log_df
