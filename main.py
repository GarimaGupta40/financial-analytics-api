from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from sec_client import sec_client
import xbrl_parser
import financial_metrics
import valuation_engine
import peer_analysis
import acquisition_scoring
import trend_analysis

from database import SessionLocal, engine
import models

# Ensure tables are created
try:
    models.Base.metadata.create_all(bind=engine)
    print("Database connected successfully")
except Exception as e:
    print("Database connection failed:", e)

app = FastAPI(
    title="Financial Data Extraction & Acquisition Analytics API",
    description="Production-level SEC XBRL data pipeline and analytics engine.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_event():
    await sec_client.close()

async def build_full_report(ticker: str, form_type: str = "10-K"):
    ticker_upper = ticker.upper()
    cik = await xbrl_parser.get_cik_from_ticker(ticker_upper)
    subs = await xbrl_parser.get_company_submissions(cik)
    
    facts = await xbrl_parser.get_company_facts(cik)
    facts_gaap = facts.get("facts", {}).get("us-gaap", {})
    
    statements = xbrl_parser.extract_financial_data(facts_gaap)
    historical = xbrl_parser.get_historical_data(facts_gaap)
    
    metrics = financial_metrics.calculate_metrics(statements)
    growth = financial_metrics.calculate_growth(statements, historical)
    
    valuation = await valuation_engine.calculate_valuation(ticker_upper, statements)
    metrics["valuation"] = valuation
    
    peers = await peer_analysis.get_peer_comparison(cik, subs.get("sic", ""), ticker_upper, metrics)
    acq = acquisition_scoring.score_acquisition(metrics, growth, statements)
    
    recent_forms = subs.get("filings", {}).get("recent", {})
    forms = recent_forms.get("form", [])
    dates = recent_forms.get("filingDate", [])
    
    match_idx = -1
    for i, form in enumerate(forms):
        if form.upper() == form_type.upper():
            match_idx = i
            break
            
    if match_idx == -1:
        raise HTTPException(status_code=404, detail=f"No {form_type} filings found for {ticker.upper()}.")
        
    filing_date = dates[match_idx] if match_idx < len(dates) else ""

    return {
        "company_info": {
            "ticker": ticker_upper,
            "company_name": subs.get("name"),
            "cik": cik,
            "form_type": form_type.upper(),
            "filing_date": filing_date
        },
        "financial_statements": statements,
        "financial_metrics": metrics,
        "growth_metrics": growth,
        "acquisition_indicators": acq,
        "metadata": {
            "data_source": "SEC EDGAR XBRL",
            "currency": "USD",
            "units": "full",
            "extraction_timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

@app.get("/company/{ticker}")
async def get_company(ticker: str):
    cik = await xbrl_parser.get_cik_from_ticker(ticker)
    subs = await xbrl_parser.get_company_submissions(cik)
    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "company_name": subs.get("name"),
        "sic": subs.get("sic")
    }

@app.get("/financials/{ticker}")
async def get_financials(ticker: str):
    cik = await xbrl_parser.get_cik_from_ticker(ticker)
    facts = await xbrl_parser.get_company_facts(cik)
    facts_gaap = facts.get("facts", {}).get("us-gaap", {})
    statements = xbrl_parser.extract_financial_data(facts_gaap)
    return {"financial_statements": statements}

@app.get("/metrics/{ticker}")
async def get_metrics(ticker: str):
    res = await build_full_report(ticker)
    return {
        "financial_metrics": res["financial_metrics"],
        "growth_metrics": res["growth_metrics"]
    }

@app.get("/peer-analysis/{ticker}")
async def get_peer_analysis(ticker: str):
    ticker_upper = ticker.upper()
    cik = await xbrl_parser.get_cik_from_ticker(ticker_upper)
    subs = await xbrl_parser.get_company_submissions(cik)
    peers = await peer_analysis.get_peer_comparison(cik, subs.get("sic", ""), ticker_upper, {})
    return {"peer_comparison": peers}

@app.get("/acquisition-score/{ticker}")
async def get_acquisition_score(ticker: str):
    res = await build_full_report(ticker)
    return {"acquisition_score": res["acquisition_indicators"]}
    
def insert_report_to_db(report: dict):
    db = SessionLocal()
    try:
        c_info = report["company_info"]
        
        # Insert or update company
        existing_company = db.query(models.Company).filter(models.Company.ticker == c_info["ticker"]).first()
        if existing_company:
            existing_company.company_name = c_info["company_name"]
            existing_company.cik = c_info["cik"]
            existing_company.form_type = c_info["form_type"]
            existing_company.filing_date = c_info["filing_date"]
            db.commit()
            db.refresh(existing_company)
            company_id = existing_company.id
        else:
            company = models.Company(
                ticker=c_info["ticker"],
                company_name=c_info["company_name"],
                cik=c_info["cik"],
                form_type=c_info["form_type"],
                filing_date=c_info["filing_date"]
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            company_id = company.id

        filing_date = c_info["filing_date"]

        fs_exists = db.query(models.FinancialStatement).filter(
            models.FinancialStatement.company_id == company_id,
            models.FinancialStatement.filing_date == filing_date
        ).first()

        if fs_exists:
            db.query(models.FinancialStatement).filter(models.FinancialStatement.company_id == company_id, models.FinancialStatement.filing_date == filing_date).delete()
            db.query(models.FinancialMetric).filter(models.FinancialMetric.company_id == company_id, models.FinancialMetric.filing_date == filing_date).delete()
            db.query(models.GrowthMetric).filter(models.GrowthMetric.company_id == company_id, models.GrowthMetric.filing_date == filing_date).delete()
            db.query(models.AcquisitionIndicator).filter(models.AcquisitionIndicator.company_id == company_id, models.AcquisitionIndicator.filing_date == filing_date).delete()
            db.query(models.Metadata).filter(models.Metadata.company_id == company_id, models.Metadata.filing_date == filing_date).delete()
            db.commit()

        fs = report["financial_statements"]
        fstmt = models.FinancialStatement(
            company_id=company_id,
            filing_date=filing_date,
            revenue=fs["income_statement"]["revenue"],
            cost_of_revenue=fs["income_statement"]["cost_of_revenue"],
            gross_profit=fs["income_statement"]["gross_profit"],
            operating_income=fs["income_statement"]["operating_income"],
            net_income=fs["income_statement"]["net_income"],
            interest_expense=fs["income_statement"]["interest_expense"],
            income_tax=fs["income_statement"]["income_tax"],
            ebit=fs["income_statement"]["ebit"],
            ebitda=fs["income_statement"]["ebitda"],
            operating_cash_flow=fs["cash_flow"]["operating_cash_flow"],
            capital_expenditure=fs["cash_flow"]["capital_expenditure"],
            depreciation=fs["cash_flow"]["depreciation"],
            free_cash_flow=fs["cash_flow"]["free_cash_flow"],
        )
        db.add(fstmt)

        fm = report["financial_metrics"]
        fmetric = models.FinancialMetric(
            company_id=company_id,
            filing_date=filing_date,
            gross_margin=fm["profitability"]["gross_margin"],
            operating_margin=fm["profitability"]["operating_margin"],
            net_profit_margin=fm["profitability"]["net_profit_margin"],
            roa=fm["profitability"]["roa"],
            roe=fm["profitability"]["roe"],
            roic=fm["profitability"]["roic"],
            ebitda_margin=fm["profitability"]["ebitda_margin"],
            current_ratio=fm["liquidity"]["current_ratio"],
            quick_ratio=fm["liquidity"]["quick_ratio"],
            cash_ratio=fm["liquidity"]["cash_ratio"],
            debt_to_equity=fm["solvency"]["debt_to_equity"],
            debt_to_assets=fm["solvency"]["debt_to_assets"],
            interest_coverage_ratio=fm["solvency"]["interest_coverage_ratio"],
            price_to_earnings=fm["valuation"]["price_to_earnings"] if fm.get("valuation") else None,
            price_to_book=fm["valuation"]["price_to_book"] if fm.get("valuation") else None,
            price_to_sales=fm["valuation"]["price_to_sales"] if fm.get("valuation") else None,
            enterprise_value=fm["valuation"]["enterprise_value"] if fm.get("valuation") else None,
            ev_to_ebitda=fm["valuation"]["ev_to_ebitda"] if fm.get("valuation") else None,
        )
        db.add(fmetric)

        gm = report["growth_metrics"]
        gmetric = models.GrowthMetric(
            company_id=company_id,
            filing_date=filing_date,
            revenue_growth_yoy=gm["revenue_growth_yoy"],
            net_income_growth_yoy=gm["net_income_growth_yoy"],
            free_cash_flow_growth=gm["free_cash_flow_growth"]
        )
        db.add(gmetric)

        ai = report["acquisition_indicators"]
        aindicator = models.AcquisitionIndicator(
            company_id=company_id,
            filing_date=filing_date,
            financial_distress=ai["financial_distress"],
            valuation_attractiveness=ai["valuation_attractiveness"],
            market_position=ai["market_position"],
            operational_efficiency=ai["operational_efficiency"]
        )
        db.add(aindicator)

        md = report["metadata"]
        mdata = models.Metadata(
            company_id=company_id,
            filing_date=filing_date,
            data_source=md["data_source"],
            currency=md["currency"],
            units=md["units"],
            extraction_timestamp=datetime.fromisoformat(md["extraction_timestamp"].replace("Z", "+00:00")) if "extraction_timestamp" in md else None
        )
        db.add(mdata)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error inserting into DB: {e}")
    finally:
        db.close()

@app.get("/trend-analysis/{ticker}")
def get_trend_analysis(ticker: str):
    db = SessionLocal()
    try:
        result = trend_analysis.analyze_company_trends(db, ticker)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    finally:
        db.close()

@app.get("/report/{ticker}")
async def get_report(
    ticker: str = Path(..., description="Company ticker, e.g. AAPL"),
    form_type: str = Query("10-K", description="Filing type (10-K, 10-Q, 8-K)")
):
    report = await build_full_report(ticker, form_type)
    # Insert report into the database
    insert_report_to_db(report)
    return report

@app.get("/filing/latest")
async def get_latest_compat(
    ticker: str = Query(..., description="Company ticker, e.g. AAPL"),
    form_type: str = Query("10-K", description="Filing type (10-K, 10-Q, 8-K)")
):
    report = await build_full_report(ticker, form_type)
    # Insert report into the database
    insert_report_to_db(report)
    return report

@app.get("/")
def root():
    return {"message": "Advanced XBRL Financial API Running."}
