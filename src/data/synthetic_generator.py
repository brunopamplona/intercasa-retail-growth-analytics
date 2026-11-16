"""
Synthetic data generator — InterCasa Retail Growth Analytics.

WARNING: All data generated here is 100% synthetic.
No real customer, transaction, or media data from InterCasa Móveis is used.
Parameters are calibrated against published benchmarks for Brazilian
omnichannel furniture retail and e-commerce (2015–2020).

Seed = 42 ensures full reproducibility.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ── Source-of-truth constants (from CV / industry benchmarks) ────────────────

CHANNELS = {
    "Google Ads": {"share": 0.40, "cac": 180, "avg_roas": 3.2},
    "Meta Ads":   {"share": 0.25, "cac": 220, "avg_roas": 2.6},
    "SEO":        {"share": 0.20, "cac":  80, "avg_roas": 6.1},
    "CRM":        {"share": 0.15, "cac":  40, "avg_roas": 9.4},
}

PRODUCT_CATEGORIES = {
    "Sala de Estar":  {"share": 0.35, "avg_ticket": 2800},
    "Quarto":         {"share": 0.28, "avg_ticket": 3400},
    "Escritório":     {"share": 0.20, "avg_ticket": 1600},
    "Cozinha":        {"share": 0.12, "avg_ticket": 1900},
    "Área Externa":   {"share": 0.05, "avg_ticket":  950},
}

PAYMENT_METHODS = {
    "Cartão de Crédito (12x)": {"share": 0.52},
    "Cartão de Crédito (à vista)": {"share": 0.18},
    "Boleto Bancário":        {"share": 0.22},
    "Transferência":          {"share": 0.08},
}

MONTHLY_MEDIA_BUDGET = 33_000   # R$ midpoint of R$300–500K/year ÷ 12
START_DATE = datetime(2015, 1, 1)
END_DATE   = datetime(2019, 12, 31)


# ── Generators ───────────────────────────────────────────────────────────────

def generate_customers(n: int = 2000, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic customer base with acquisition metadata and LTV signals.
    High-ticket, low-frequency retail: avg AOV ~R$2,400, avg 1.3 purchases/lifetime.
    """
    rng = np.random.default_rng(seed)

    ch_names   = list(CHANNELS.keys())
    ch_weights = [CHANNELS[c]["share"] for c in ch_names]
    channels   = rng.choice(ch_names, size=n, p=ch_weights)

    acq_days = rng.integers(0, (END_DATE - START_DATE).days - 180, size=n)
    acq_dates = [START_DATE + timedelta(days=int(d)) for d in acq_days]

    cacs = np.array([CHANNELS[c]["cac"] * rng.uniform(0.85, 1.20) for c in channels]).round(2)

    cat_names   = list(PRODUCT_CATEGORIES.keys())
    cat_weights = [PRODUCT_CATEGORIES[c]["share"] for c in cat_names]
    first_cat   = rng.choice(cat_names, size=n, p=cat_weights)

    avg_ticket = np.array([PRODUCT_CATEGORIES[c]["avg_ticket"] for c in first_cat])
    first_aov  = (avg_ticket * rng.uniform(0.75, 1.30, size=n)).round(2)

    # Lifetime: 18–42 months (furniture buyers stay long, buy rarely)
    lifetime_months = rng.integers(18, 43, size=n)

    # 30% buy a second time; 8% buy a third time
    n_purchases = np.ones(n, dtype=int)
    second      = rng.random(n) < 0.30
    third       = rng.random(n) < 0.08
    n_purchases += second.astype(int) + third.astype(int)

    ltv = (first_aov * n_purchases * 0.40).round(2)   # 40% contribution margin

    rfm_recency  = rng.integers(1, lifetime_months + 1)
    rfm_freq     = n_purchases
    rfm_monetary = first_aov

    df = pd.DataFrame({
        "customer_id":        [f"cust_{i:05d}" for i in range(n)],
        "acquisition_channel": channels,
        "acquisition_date":   acq_dates,
        "cac":                cacs,
        "first_category":     first_cat,
        "first_aov":          first_aov,
        "n_purchases":        n_purchases,
        "lifetime_months":    lifetime_months,
        "ltv_contribution":   ltv,
        "rfm_recency_months": rfm_recency,
        "rfm_frequency":      rfm_freq,
        "rfm_monetary":       rfm_monetary,
    })
    return df


def generate_ab_checkout(n_per_arm: int = 1500, seed: int = 42) -> pd.DataFrame:
    """
    A/B experiment: optimized checkout (treatment) vs. original (control).
    CV benchmark: ~13% improvement in conversion rate.
    Control CVR ~2.8%, Treatment CVR ~3.16%.
    """
    rng = np.random.default_rng(seed)

    control_cvr   = 0.028
    treatment_cvr = control_cvr * 1.13   # +13%

    pay_names   = list(PAYMENT_METHODS.keys())
    pay_weights = [PAYMENT_METHODS[p]["share"] for p in pay_names]

    rows = []
    for arm, cvr in [("control", control_cvr), ("treatment", treatment_cvr)]:
        converted   = rng.random(n_per_arm) < cvr
        session_aov = rng.uniform(900, 4500, n_per_arm).round(2)
        payment     = rng.choice(pay_names, size=n_per_arm, p=pay_weights)

        # Treatment: slightly higher AOV (trust signals reduce price anxiety)
        if arm == "treatment":
            session_aov *= rng.uniform(1.00, 1.05, n_per_arm)

        for i in range(n_per_arm):
            rows.append({
                "arm":          arm,
                "session_id":   f"{arm[:3]}_{i:05d}",
                "converted":    int(converted[i]),
                "session_aov":  round(session_aov[i], 2) if converted[i] else 0.0,
                "payment_method": payment[i] if converted[i] else None,
                "device":       rng.choice(["desktop", "mobile", "tablet"],
                                           p=[0.52, 0.38, 0.10]),
            })

    return pd.DataFrame(rows)


def generate_media_mix(seed: int = 42) -> pd.DataFrame:
    """
    Monthly media spend and revenue attribution for Google Ads + Meta (2015–2019).
    Total budget: R$300–500K/year. 48 months.
    """
    rng = np.random.default_rng(seed)

    paid_channels = ["Google Ads", "Meta Ads"]
    paid_split    = {"Google Ads": 0.60, "Meta Ads": 0.40}

    rows = []
    current = START_DATE
    month_idx = 0
    while current <= END_DATE:
        total_budget = MONTHLY_MEDIA_BUDGET * rng.uniform(0.80, 1.25)
        # Seasonal: higher in Nov-Dec (Black Friday/Christmas)
        if current.month in [11, 12]:
            total_budget *= 1.35
        elif current.month in [1, 2]:
            total_budget *= 0.80

        for ch in paid_channels:
            spend = total_budget * paid_split[ch] * rng.uniform(0.90, 1.10)
            roas  = CHANNELS[ch]["avg_roas"] * rng.uniform(0.75, 1.30)
            clicks = int(spend / rng.uniform(1.80, 3.50))
            conv   = int(clicks * rng.uniform(0.008, 0.018))
            revenue = spend * roas

            rows.append({
                "year_month":   current.strftime("%Y-%m"),
                "month_idx":    month_idx,
                "channel":      ch,
                "spend_brl":    round(spend, 2),
                "clicks":       clicks,
                "conversions":  conv,
                "revenue_brl":  round(revenue, 2),
                "roas":         round(roas, 3),
                "cpa":          round(spend / max(conv, 1), 2),
            })

        current = (current.replace(day=1) + timedelta(days=32)).replace(day=1)
        month_idx += 1

    return pd.DataFrame(rows)
