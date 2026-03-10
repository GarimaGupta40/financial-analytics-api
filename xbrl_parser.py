from fastapi import HTTPException
from typing import Optional
from datetime import datetime
from sec_client import sec_client


# ─────────────────────────────────────────────────────────────────────────────
# SEC EDGAR helpers
# ─────────────────────────────────────────────────────────────────────────────

async def get_cik_from_ticker(ticker: str) -> str:
    url = "https://www.sec.gov/files/company_tickers.json"
    data = await sec_client.get(url)
    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry["ticker"].upper() == ticker_upper:
            return str(entry["cik_str"]).zfill(10)
    raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found.")

async def get_company_submissions(cik: str) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    return await sec_client.get(url)

async def get_company_facts(cik: str) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    try:
        return await sec_client.get(url)
    except HTTPException:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Core XBRL extraction helper
# ─────────────────────────────────────────────────────────────────────────────

def get_value(facts: dict, tag: str, year_offset: int = 0) -> Optional[float]:
    """
    Extract the most recent fiscal-year value for an XBRL tag.
    Prioritizes fp == 'FY' and form == '10-K'.
    """
    if tag not in facts:
        return None

    units = facts[tag].get("units", {})
    if "USD" in units:
        data_points = units["USD"]
    elif units:
        data_points = next(iter(units.values()))
    else:
        return None

    if not data_points:
        return None

    # Filter for annual reports (FY + 10-K) and no segment
    annual_points = [
        p for p in data_points
        if p.get("fp") == "FY" 
        and p.get("form") == "10-K"
        and p.get("segment") is None
    ]

    # If no strict 10-K FY, try any FY no segment
    if not annual_points:
        annual_points = [
            p for p in data_points
            if p.get("fp") == "FY"
            and p.get("segment") is None
        ]

    # If still nothing, take all no-segment and we'll sort by date
    if not annual_points:
        annual_points = [p for p in data_points if p.get("segment") is None]

    if not annual_points:
        return None

    # Sort by end date descending
    annual_points.sort(key=lambda x: x.get("end", "0000-00-00"), reverse=True)

    if year_offset == 0:
        return float(annual_points[0]["val"])
    else:
        # Looking for a prior year
        latest_end = annual_points[0]["end"]
        latest_year = int(latest_end[:4])
        target_year = latest_year - year_offset
        
        target_points = [
            p for p in annual_points 
            if p.get("end", "").startswith(str(target_year))
        ]
        if not target_points:
            return None
        target_points.sort(key=lambda x: x.get("end", "0000-00-00"), reverse=True)
        return float(target_points[0]["val"])


def get_best_value(facts: dict, tag_list: list, year_offset: int = 0) -> Optional[float]:
    """
    Returns the largest fiscal-year value found among multiple potential tags.
    This helps pick the consolidated total for companies like Microsoft.
    """
    values = []
    for tag in tag_list:
        val = get_value(facts, tag, year_offset)
        if val is not None:
            values.append(val)
    
    if not values:
        return None
    
    return max(values)


# ─────────────────────────────────────────────────────────────────────────────
# Tag priority lists
# ─────────────────────────────────────────────────────────────────────────────

REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet"
]

COST_TAGS = [
    "CostOfRevenue",
    "CostOfGoodsAndServicesSold",
    "CostOfSales"
]


# ─────────────────────────────────────────────────────────────────────────────
# Regex fallback (placeholder)
# ─────────────────────────────────────────────────────────────────────────────

def regex_parse_from_table(text: str, metric_name: str) -> Optional[float]:
    # Regex table parsing fallback placeholder
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Financial data extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_financial_data(facts_gaap: dict, text: str = ""):
    # ── Income statement ────────────────────────────────────────────────────
    revenue = get_best_value(facts_gaap, REVENUE_TAGS)
    if revenue is None:
        revenue = regex_parse_from_table(text, "Revenues")

    cost_of_revenue = get_best_value(facts_gaap, COST_TAGS)
    if cost_of_revenue is None:
        cost_of_revenue = regex_parse_from_table(text, "CostOfRevenue")

    # Always recompute gross_profit if revenue and cost are available
    gross_profit = None
    if revenue is not None and cost_of_revenue is not None:
        gross_profit = revenue - cost_of_revenue
    
    if gross_profit is None:
        gross_profit = get_value(facts_gaap, "GrossProfit")
    if gross_profit is None:
        gross_profit = regex_parse_from_table(text, "GrossProfit")

    operating_income = get_value(facts_gaap, "OperatingIncomeLoss")
    if operating_income is None:
        operating_income = regex_parse_from_table(text, "OperatingIncomeLoss")

    net_income = get_value(facts_gaap, "NetIncomeLoss")
    if net_income is None:
        net_income = regex_parse_from_table(text, "NetIncomeLoss")

    interest_expense = get_value(facts_gaap, "InterestExpense")
    if interest_expense is None:
        interest_expense = regex_parse_from_table(text, "InterestExpense")

    income_tax = get_value(facts_gaap, "IncomeTaxExpenseBenefit")
    if income_tax is None:
        income_tax = regex_parse_from_table(text, "IncomeTaxExpenseBenefit")

    ebit = operating_income

    # ── Balance sheet ────────────────────────────────────────────────────────
    total_assets = get_value(facts_gaap, "Assets")
    if total_assets is None:
        total_assets = regex_parse_from_table(text, "Assets")

    total_liabilities = get_value(facts_gaap, "Liabilities")
    if total_liabilities is None:
        total_liabilities = regex_parse_from_table(text, "Liabilities")

    shareholder_equity = get_value(facts_gaap, "StockholdersEquity")
    if shareholder_equity is None:
        shareholder_equity = regex_parse_from_table(text, "StockholdersEquity")

    cash_and_equivalents = get_value(facts_gaap, "CashAndCashEquivalentsAtCarryingValue")
    if cash_and_equivalents is None:
        cash_and_equivalents = regex_parse_from_table(text, "CashAndCashEquivalentsAtCarryingValue")

    short_term_debt = get_value(facts_gaap, "DebtCurrent")
    if short_term_debt is None:
        short_term_debt = regex_parse_from_table(text, "DebtCurrent")

    long_term_debt = get_value(facts_gaap, "LongTermDebt")
    if long_term_debt is None:
        long_term_debt = regex_parse_from_table(text, "LongTermDebt")

    current_assets = get_value(facts_gaap, "AssetsCurrent")
    if current_assets is None:
        current_assets = regex_parse_from_table(text, "AssetsCurrent")

    current_liabilities = get_value(facts_gaap, "LiabilitiesCurrent")
    if current_liabilities is None:
        current_liabilities = regex_parse_from_table(text, "LiabilitiesCurrent")

    receivables = get_value(facts_gaap, "AccountsReceivableNetCurrent")
    if receivables is None:
        receivables = regex_parse_from_table(text, "AccountsReceivableNetCurrent")

    # ── Cash flow ────────────────────────────────────────────────────────────
    operating_cash_flow = get_value(facts_gaap, "NetCashProvidedByUsedInOperatingActivities")
    if operating_cash_flow is None:
        operating_cash_flow = regex_parse_from_table(text, "NetCashProvidedByUsedInOperatingActivities")

    capital_expenditure = get_value(facts_gaap, "PaymentsToAcquirePropertyPlantAndEquipment")
    if capital_expenditure is None:
        capital_expenditure = regex_parse_from_table(text, "PaymentsToAcquirePropertyPlantAndEquipment")

    depreciation = get_value(facts_gaap, "DepreciationDepletionAndAmortization")
    if depreciation is None:
        depreciation = regex_parse_from_table(text, "DepreciationDepletionAndAmortization")

    # ── Derived ──────────────────────────────────────────────────────────────
    ebitda = None
    if ebit is not None and depreciation is not None:
        ebitda = ebit + depreciation
    elif ebit is not None:
        ebitda = ebit

    free_cash_flow = None
    if operating_cash_flow is not None:
        free_cash_flow = operating_cash_flow - abs(capital_expenditure or 0)

    return {
        "income_statement": {
            "revenue":          revenue,
            "cost_of_revenue":  cost_of_revenue,
            "gross_profit":     gross_profit,
            "operating_income": operating_income,
            "net_income":       net_income,
            "interest_expense": interest_expense,
            "income_tax":       income_tax,
            "ebit":             ebit,
            "ebitda":           ebitda,
        },
        "balance_sheet": {
            "total_assets":        total_assets,
            "total_liabilities":   total_liabilities,
            "shareholder_equity":  shareholder_equity,
            "cash_and_equivalents": cash_and_equivalents,
            "short_term_debt":     short_term_debt,
            "long_term_debt":      long_term_debt,
            "current_assets":      current_assets,
            "current_liabilities": current_liabilities,
            "receivables":         receivables,
        },
        "cash_flow": {
            "operating_cash_flow": operating_cash_flow,
            "capital_expenditure": capital_expenditure,
            "depreciation":        depreciation,
            "free_cash_flow":      free_cash_flow,
        },
    }


def get_historical_data(facts_gaap: dict) -> dict:
    revenue_prev    = get_best_value(facts_gaap, REVENUE_TAGS, 1)
    net_income_prev = get_value(facts_gaap, "NetIncomeLoss", 1)
    ocf_prev        = get_value(facts_gaap, "NetCashProvidedByUsedInOperatingActivities", 1)
    capex_prev      = get_value(facts_gaap, "PaymentsToAcquirePropertyPlantAndEquipment", 1)

    fcf_prev = None
    if ocf_prev is not None and capex_prev is not None:
        fcf_prev = ocf_prev - abs(capex_prev)

    return {
        "revenue_prev":        revenue_prev,
        "net_income_prev":     net_income_prev,
        "free_cash_flow_prev": fcf_prev,
    }
