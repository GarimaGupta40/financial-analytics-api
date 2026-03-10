def safe_div(num, den):
    if num is None or den is None or den == 0:
        return None
    return round(num / den, 4)

def calculate_metrics(statements: dict) -> dict:
    inc = statements["income_statement"]
    bal = statements["balance_sheet"]
    
    rev = inc["revenue"]
    net_income = inc["net_income"]
    operating_income = inc["operating_income"]
    gross_profit = inc["gross_profit"]
    ebitda = inc["ebitda"]
    interest_expense = inc["interest_expense"]
    ebit = inc["ebit"]
    
    total_assets = bal["total_assets"]
    total_liabilities = bal["total_liabilities"]
    equity = bal["shareholder_equity"]
    st_debt = bal["short_term_debt"] or 0
    lt_debt = bal["long_term_debt"] or 0
    total_debt = st_debt + lt_debt if (bal["short_term_debt"] is not None or bal["long_term_debt"] is not None) else None
    cash = bal["cash_and_equivalents"]
    
    gross_margin = safe_div(gross_profit, rev)
    operating_margin = safe_div(operating_income, rev)
    net_profit_margin = safe_div(net_income, rev)
    roa = safe_div(net_income, total_assets)
    roe = safe_div(net_income, equity)
    
    nopat = None
    if ebit is not None and inc["income_tax"] is not None:
        tax_rate = safe_div(inc["income_tax"], operating_income) or 0.21
        nopat = ebit * (1 - tax_rate)
    elif ebit is not None:
        # Default ~21% tech tax rate if unlisted
        nopat = ebit * 0.79
    
    invested_capital = None
    if total_debt is not None and equity is not None:
        invested_capital = total_debt + equity
        
    roic = safe_div(nopat, invested_capital)
    ebitda_margin = safe_div(ebitda, rev)
    
    debt_to_equity = safe_div(total_debt, equity)
    debt_to_assets = safe_div(total_debt, total_assets)
    interest_coverage_ratio = safe_div(ebit, interest_expense)
    if interest_coverage_ratio is not None:
        interest_coverage_ratio = abs(interest_coverage_ratio)
        
    current_assets = bal.get("current_assets")
    current_liabilities = bal.get("current_liabilities")
    receivables = bal.get("receivables")
    
    current_ratio = safe_div(current_assets, current_liabilities)
    
    quick_ratio = None
    if cash is not None and receivables is not None:
        quick_ratio = safe_div(cash + receivables, current_liabilities)
    elif cash is not None:
        quick_ratio = safe_div(cash, current_liabilities)
        
    cash_ratio = safe_div(cash, current_liabilities)

    return {
        "profitability": {
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "net_profit_margin": net_profit_margin,
            "roa": roa,
            "roe": roe,
            "roic": roic,
            "ebitda_margin": ebitda_margin
        },
        "liquidity": {
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "cash_ratio": cash_ratio
        },
        "solvency": {
            "debt_to_equity": debt_to_equity,
            "debt_to_assets": debt_to_assets,
            "interest_coverage_ratio": interest_coverage_ratio
        }
    }

def calculate_growth(statements: dict, historical: dict) -> dict:
    inc = statements.get("income_statement", {})
    cash = statements.get("cash_flow", {})
    
    rev_curr = inc.get("revenue")
    rev_prev = historical.get("revenue_prev")
    
    ni_curr = inc.get("net_income")
    ni_prev = historical.get("net_income_prev")
    
    fcf_curr = cash.get("free_cash_flow")
    fcf_prev = historical.get("free_cash_flow_prev")
    
    rev_growth = safe_div(rev_curr - rev_prev, rev_prev) if rev_curr is not None and rev_prev is not None else None
    ni_growth = safe_div(ni_curr - ni_prev, ni_prev) if ni_curr is not None and ni_prev is not None else None
    fcf_growth = safe_div(fcf_curr - fcf_prev, fcf_prev) if fcf_curr is not None and fcf_prev is not None else None
    
    return {
        "revenue_growth_yoy": rev_growth,
        "net_income_growth_yoy": ni_growth,
        "free_cash_flow_growth": fcf_growth
    }
