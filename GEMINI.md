# Project Context: German Wealth & Retirement Architect (2026)

## 1. Mathematical Ground Truth (2026 Constants)
The following constants are immutable for this project. All calculations in `calculations.py` must reference these:

### Stock Market (Depot)
- **Basiszins (Vorabpauschale 2026):** 3.20%
- **Basisertrag Factor:** 0.70
- **Partial Exemption (Teilfreistellung):** 30% for equity funds.
- **Sparerpauschbetrag:** €1,000 (Individual).
- **Abgeltungsteuer:** 25% + 5.5% Solidaritätszuschlag (effective 26.375%).

### Statutory Pension (GRV)
- **Rentenwert (Current):** €40.79
- **Rentenwert (from July 1, 2026):** €42.52
- **Average Yearly Earnings (Provisional 2026):** €51,944 (equals 1 Entgeltpunkt).
- **Beitragsbemessungsgrenze (Rente):** €101,400 per year.

### Health Insurance (GKV/PV) - 2026 Rates
- **General Rate:** 14.6%
- **Avg. Zusatzbeitrag 2026:** 2.9% (Total GKV: 17.5%)
- **Pflegeversicherung (PV):** 3.6% (with children) or 4.2% (childless).
- **BBG (GKV/PV):** €69,750 per year.

## 2. Core Business Logic Rules
- **Private Pension Phase 1 (Until Age 50):** Active monthly deposits + Fee structure.
- **Private Pension Phase 2 (Age 50 to 62):** Passive growth only. No deposits.
- **Private Pension Phase 3 (Age 62 to End-Age):** Annuity payout (Kapitalverzehr).
- **12/62 Rule (Halbeinkünfteverfahren):** 1. Calculate Profit (Payout - Total Deposits).
    2. Apply 15% partial exemption.
    3. Tax only 50% of the remaining at the user's marginal income tax rate.
- **GKV Payout Logic:** - **KVdR Mode:** Retiree pays GKV/PV only on the State Pension (State pays 50% of GKV). Stocks/Private Insurance are GKV-free.
    - **Voluntary Mode:** Retiree pays full GKV/PV (approx. 21%) on ALL income (Pension + Insurance + Stock Gains).

## 3. Technical Requirements
- **Language:** Python 3.12+
- **Framework:** Streamlit for UI, Plotly for Interactive Charts.
- **Architecture:** Keep logic in `calculations.py` and UI in `app.py`.
- **Formatting:** Use Type Hints and Docstrings for all functions.