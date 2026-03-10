import sys
sys.path.append('c:/Users/garim/OneDrive/Desktop/FastAPI01/FastAPI01')
import json
import main
from database import engine

report = {
    "company_info":  {
        "ticker":  "AAPL",
        "company_name":  "Apple Inc.",
        "cik":  "0000320193",
        "form_type":  "10-K",
        "filing_date":  "2025-10-31"
    },
    "financial_statements":  {
        "income_statement":  {
            "revenue":  416161000000.0,
            "cost_of_revenue":  220960000000.0, 
            "gross_profit":  195201000000.0,    
            "operating_income":  133050000000.0,
            "net_income":  112010000000.0,      
            "interest_expense":  3933000000.0,  
            "income_tax":  20719000000.0,       
            "ebit":  133050000000.0,
            "ebitda":  144748000000.0
        },
        "balance_sheet":  {
            "total_assets":  359241000000.0,       
            "total_liabilities":  285508000000.0,  
            "shareholder_equity":  73733000000.0,  
            "cash_and_equivalents":  35934000000.0,
            "short_term_debt":  None,
            "long_term_debt":  90678000000.0,      
            "current_assets":  147957000000.0,
            "current_liabilities":  165631000000.0,
            "receivables":  39777000000.0
        },
        "cash_flow":  {
            "operating_cash_flow":  111482000000.0,
            "capital_expenditure":  12715000000.0,
            "depreciation":  11698000000.0,
            "free_cash_flow":  98767000000.0
        }
    },
    "financial_metrics":  {
        "profitability":  {
            "gross_margin":  0.4691,
            "operating_margin":  0.3197,
            "net_profit_margin":  0.2692,
            "roa":  0.3118,
            "roe":  1.5191,
            "roic":  0.6833,
            "ebitda_margin":  0.3478
        },
        "liquidity":  {
            "current_ratio":  0.8933,
            "quick_ratio":  0.4571,
            "cash_ratio":  0.217
        },
        "solvency":  {
            "debt_to_equity":  1.2298,
            "debt_to_assets":  0.2524,
            "interest_coverage_ratio":  33.8291
        },
        "valuation":  {
            "price_to_earnings":  33.7838,
            "price_to_book":  51.322,
            "price_to_sales":  9.0929,
            "enterprise_value":  3838871807488.0,
            "ev_to_ebitda":  26.5211
        }
    },
    "growth_metrics":  {
        "revenue_growth_yoy":  0.0643,
        "net_income_growth_yoy":  0.195,
        "free_cash_flow_growth":  -0.0923
    },
    "acquisition_indicators":  {
        "financial_distress":  0,
        "valuation_attractiveness":  30,
        "market_position":  70,
        "operational_efficiency":  70
    },
    "metadata":  {
        "data_source":  "SEC EDGAR XBRL",
        "currency":  "USD",
        "units":  "full",
        "extraction_timestamp":  "2026-03-09T06:28:20.879120Z"
    }
}

try:
    main.insert_report_to_db(report)
except:
    import traceback
    traceback.print_exc()

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

main.insert_report_to_db(report)
