from sqlalchemy.orm import Session
from sqlalchemy import asc
import models

from typing import Optional

def calculate_cagr(beginning_value: float, ending_value: float, years: int) -> Optional[float]:
    if beginning_value is None or ending_value is None:
        return None
    if beginning_value <= 0 or years <= 0:
        return None
    try:
        return (ending_value / beginning_value) ** (1 / years) - 1
    except Exception:
        return None

def determine_trend(cagr: float) -> str:
    if cagr is None:
        return "insufficient data"
    if cagr > 0.05:
        return "growing"
    elif cagr < -0.05:
        return "declining"
    else:
        return "stable"

def analyze_company_trends(db: Session, ticker: str):
    ticker_upper = ticker.upper()
    
    # 1. Fetch company ID
    company = db.query(models.Company).filter(models.Company.ticker == ticker_upper).first()
    if not company:
        return {"error": f"Company {ticker_upper} not found in database."}

    # 2. Fetch historical financial data from financial_statements
    statements = db.query(models.FinancialStatement)\
                   .filter(models.FinancialStatement.company_id == company.id)\
                   .order_by(asc(models.FinancialStatement.filing_date))\
                   .all()

    if not statements:
        return {"error": f"No financial statements found for {ticker_upper}."}

    def get_metric_trend(metric_name: str):
        # Extract values that are not None
        values = [getattr(stmt, metric_name, None) for stmt in statements]
        values = [v for v in values if v is not None]
        
        n_periods = len(values) - 1
        
        result = {
            "3_year": {"cagr": None, "trend": "insufficient data"},
            "5_year": {"cagr": None, "trend": "insufficient data"}
        }
        
        if n_periods >= 3:
            beg_val = values[-(3 + 1)] # 3 years ago
            end_val = values[-1]
            cagr = calculate_cagr(beg_val, end_val, 3)
            result["3_year"]["cagr"] = round(cagr, 4) if cagr is not None else None
            result["3_year"]["trend"] = determine_trend(cagr)
            
        if n_periods >= 5:
            beg_val = values[-(5 + 1)] # 5 years ago
            end_val = values[-1]
            cagr = calculate_cagr(beg_val, end_val, 5)
            result["5_year"]["cagr"] = round(cagr, 4) if cagr is not None else None
            result["5_year"]["trend"] = determine_trend(cagr)
            
        return result

    revenue_trend = get_metric_trend("revenue")
    net_income_trend = get_metric_trend("net_income")
    fcf_trend = get_metric_trend("free_cash_flow")

    return {
        "ticker": ticker_upper,
        "data_points_available": len(statements),
        "trends": {
            "revenue": revenue_trend,
            "net_income": net_income_trend,
            "free_cash_flow": fcf_trend
        }
    }
