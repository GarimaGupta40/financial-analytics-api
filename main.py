"""
SEC EDGAR Filing Text Extraction API
Pulls text from 10-K, 10-Q, 8-K, DEF 14A, Form 4, S-1 filings for any public company.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import re
import json
from typing import Optional
from bs4 import BeautifulSoup

app = FastAPI(
    title="SEC EDGAR Filing API",
    description=
    "Extract text from SEC filings (10-K, 10-Q, 8-K, DEF 14A, Form 4, S-1) for any public company.",
    version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EDGAR_BASE = "https://data.sec.gov"
EDGAR_SEARCH = "https://efts.sec.gov"
SEC_BASE = "https://www.sec.gov"

HEADERS = {
    "User-Agent":
    "SEC Filing API garimagupta112003@gmail.com",  # SEC requires User-Agent
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov"
}

SUPPORTED_FORMS = {
    "10-K":
    "Annual Report – comprehensive overview, audited financials, and risk factors",
    "10-Q": "Quarterly Report – unaudited financials for Q1-Q3",
    "8-K": "Current Report – major unscheduled corporate events",
    "DEF 14A":
    "Proxy Statement – shareholder vote info (board elections, exec compensation)",
    "4":
    "Form 4 – insider transactions (directors, officers, beneficial owners)",
    "S-1": "Registration Statement – filed prior to an IPO",
}


# ─────────────────────────────────────────────
# Helper: Resolve ticker → CIK
# ─────────────────────────────────────────────
async def get_cik_from_ticker(ticker: str) -> str:
    url = f"{SEC_BASE}/files/company_tickers.json"
    async with httpx.AsyncClient(
            headers={"User-Agent": "SEC Filing API research@example.com"
                     }) as client:
        r = await client.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry["ticker"].upper() == ticker_upper:
            return str(entry["cik_str"]).zfill(10)

    raise HTTPException(status_code=404,
                        detail=f"Ticker '{ticker}' not found in SEC database.")


# ─────────────────────────────────────────────
# Helper: Get filings list for a CIK
# ─────────────────────────────────────────────
async def get_company_submissions(cik_padded: str) -> dict:
    url = f"{EDGAR_BASE}/submissions/CIK{cik_padded}.json"
    async with httpx.AsyncClient(
            headers={"User-Agent": "SEC Filing API research@example.com"
                     }) as client:
        r = await client.get(url, timeout=15)
        if r.status_code == 404:
            raise HTTPException(status_code=404,
                                detail=f"CIK {cik_padded} not found in EDGAR.")
        r.raise_for_status()
        return r.json()


# ─────────────────────────────────────────────
# Helper: Extract text from an HTML/text filing
# ─────────────────────────────────────────────
def clean_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "head", "meta"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


# ─────────────────────────────────────────────
# Helper: Fetch filing document text
# ─────────────────────────────────────────────
async def fetch_filing_text(cik: str, accession_number: str) -> str:
    acc_clean = accession_number.replace("-", "")
    index_url = f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{acc_clean}/{accession_number}-index.htm"

    async with httpx.AsyncClient(
            headers={"User-Agent": "SEC Filing API research@example.com"},
            follow_redirects=True,
            timeout=30) as client:
        # Get the filing index to find the primary document
        r = await client.get(index_url)
        if r.status_code != 200:
            # Try alternate index URL
            index_url2 = f"{SEC_BASE}/cgi-bin/browse-edgar?action=getcompany&filenum=&State=0&SIC=&dateb=&owner=include&count=1&search_text=&action=getcompany"
            raise HTTPException(status_code=502,
                                detail="Could not retrieve filing index.")

        soup = BeautifulSoup(r.text, "html.parser")
        # Find the primary document link (first .htm or .txt that isn't the index)
        doc_link = None
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 3:
                link_tag = cells[2].find("a") if len(cells) > 2 else None
                if link_tag and link_tag.get("href"):
                    href = link_tag["href"]
                    if href.endswith((".htm", ".html",
                                      ".txt")) and "index" not in href.lower():
                        doc_link = f"{SEC_BASE}{href}"
                        break

        if not doc_link:
            # Fallback: use the accession number text file
            doc_link = f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{acc_clean}/{accession_number}.txt"

        doc_r = await client.get(doc_link, timeout=30)
        if doc_r.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Could not fetch document at {doc_link}")

        return clean_html_to_text(doc_r.text)


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════


@app.get("/", summary="API Info")
def root():
    return {
        "api": "SEC EDGAR Filing Text Extraction API",
        "supported_form_types": SUPPORTED_FORMS,
        "endpoints": {
            "GET /company/{ticker}":
            "Get company info and filing history",
            "GET /filings/{ticker}":
            "List filings by form type",
            "GET /filing/text":
            "Extract full text from a specific filing",
            "GET /filing/latest":
            "Get text from the most recent filing of a given type",
        }
    }


@app.get("/forms", summary="List supported filing types")
def list_forms():
    return {"supported_forms": SUPPORTED_FORMS}


@app.get("/company/{ticker}", summary="Get company info + recent filings")
async def get_company_info(ticker: str):
    """Resolve a ticker to its CIK and return company metadata."""
    cik = await get_cik_from_ticker(ticker)
    data = await get_company_submissions(cik)

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])

    # Group by form type
    filings_by_type: dict = {}
    for form, date, acc in zip(forms, dates, accessions):
        form_key = form.strip()
        if form_key not in filings_by_type:
            filings_by_type[form_key] = []
        if len(filings_by_type[form_key]) < 5:  # last 5 per type
            filings_by_type[form_key].append({
                "date": date,
                "accession_number": acc
            })

    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "company_name": data.get("name"),
        "sic": data.get("sic"),
        "sic_description": data.get("sicDescription"),
        "state_of_incorporation": data.get("stateOfIncorporation"),
        "fiscal_year_end": data.get("fiscalYearEnd"),
        "recent_filings_by_type": filings_by_type,
    }


@app.get("/filings/{ticker}", summary="List filings for a given form type")
async def list_filings(
    ticker: str,
    form_type: str = Query(
        ..., description="e.g. 10-K, 10-Q, 8-K, DEF 14A, 4, S-1"),
    count: int = Query(10,
                       ge=1,
                       le=40,
                       description="Number of filings to return")):
    """List filings for a company filtered by form type."""
    cik = await get_cik_from_ticker(ticker)
    data = await get_company_submissions(cik)

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    descriptions = recent.get("primaryDocument", [])

    results = []
    form_type_upper = form_type.strip().upper()

    for form, date, acc, desc in zip(forms, dates, accessions, descriptions):
        if form.strip().upper() == form_type_upper:
            results.append({
                "form_type":
                form,
                "filing_date":
                date,
                "accession_number":
                acc,
                "primary_document":
                desc,
                "filing_url":
                f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{acc.replace('-','')}/{acc}-index.htm",
            })
            if len(results) >= count:
                break

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No {form_type} filings found for {ticker.upper()}.")

    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "company_name": data.get("name"),
        "form_type": form_type,
        "count": len(results),
        "filings": results,
    }


@app.get("/filing/text", summary="Extract full text from a specific filing")
async def get_filing_text(
        ticker: str = Query(..., description="Company ticker, e.g. AAPL"),
        accession_number: str = Query(
            ..., description="Accession number, e.g. 0000320193-23-000106"),
        max_chars: int = Query(50000,
                               ge=1000,
                               le=500000,
                               description="Max characters to return")):
    """Fetch and extract clean text from a specific SEC filing by accession number."""
    cik = await get_cik_from_ticker(ticker)
    text = await fetch_filing_text(cik, accession_number)

    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "accession_number": accession_number,
        "total_chars": len(text),
        "truncated": len(text) > max_chars,
        "text": text[:max_chars],
    }


@app.get("/filing/latest",
         summary="Get text from the most recent filing of a given type")
async def get_latest_filing_text(
        ticker: str = Query(..., description="Company ticker, e.g. MSFT"),
        form_type: str = Query(
            ..., description="Filing type: 10-K, 10-Q, 8-K, DEF 14A, 4, S-1"),
        max_chars: int = Query(50000,
                               ge=1000,
                               le=500000,
                               description="Max characters to return")):
    """Fetch the most recent filing of a given type and return its extracted text."""
    cik = await get_cik_from_ticker(ticker)
    data = await get_company_submissions(cik)

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])

    form_type_upper = form_type.strip().upper()
    match = None

    for form, date, acc in zip(forms, dates, accessions):
        if form.strip().upper() == form_type_upper:
            match = {"form": form, "date": date, "accession": acc}
            break

    if not match:
        raise HTTPException(
            status_code=404,
            detail=f"No {form_type} filings found for {ticker.upper()}.")

    text = await fetch_filing_text(cik, match["accession"])

    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "company_name": data.get("name"),
        "form_type": match["form"],
        "filing_date": match["date"],
        "accession_number": match["accession"],
        "filing_url":
        f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{match['accession'].replace('-','')}/{match['accession']}-index.htm",
        "total_chars": len(text),
        "truncated": len(text) > max_chars,
        "text": text[:max_chars],
    }
