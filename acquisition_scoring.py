def score_acquisition(metrics: dict, growth: dict, statements: dict = None) -> dict:
    prof = metrics.get("profitability", {})
    solv = metrics.get("solvency", {})
    
    # Financial Distress Score (0-100)
    distress = 100
    
    # Debt ratio weight = 20
    if solv.get("debt_to_equity") is not None and solv["debt_to_equity"] < 1.5:
        distress -= 20
        
    # Profit margins weight = 30
    if prof.get("net_profit_margin") is not None and prof["net_profit_margin"] > 0:
        distress -= 30
        
    # Cash flow weight = 30
    if statements and statements.get("cash_flow", {}).get("free_cash_flow") is not None:
        if statements["cash_flow"]["free_cash_flow"] > 0:
            distress -= 30
            
    # Revenue growth weight = 20
    if growth.get("revenue_growth_yoy") is not None and growth["revenue_growth_yoy"] > 0:
        distress -= 20
        
    val = metrics.get("valuation", {})
    val_score = 50
    pe = val.get("price_to_earnings")
    if pe is not None and 0 < pe < 15: val_score += 30
    elif pe is not None and pe > 30: val_score -= 20
        
    market_score = 50
    if prof.get("roa") is not None and prof["roa"] > 0.05: market_score += 20
        
    total_score = (distress * 0.4) + (val_score * 0.4) + (market_score * 0.2)
    total_score = max(0, min(100, int(total_score)))
    
    return {
        "financial_distress": int(distress),
        "valuation_attractiveness": int(val_score),
        "market_position": int(market_score),
        "operational_efficiency": int(market_score)
    }
