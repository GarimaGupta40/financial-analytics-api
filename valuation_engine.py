import asyncio
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf
from financial_metrics import safe_div

# Thread pool for running blocking yfinance calls
_executor = ThreadPoolExecutor(max_workers=4)


def _fetch_yf_info(ticker: str) -> dict:
    """
    Blocking call — must run in a thread executor.
    Returns a normalized quote dict or {}.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info  # blocking network call
        
        price      = info.get("currentPrice") or info.get("regularMarketPrice")
        market_cap = info.get("marketCap")
        shares     = info.get("sharesOutstanding")
        
        if price is None and market_cap is None:
            return {}
        
        return {
            "price":      price,
            "market_cap": market_cap,
            "shares":     shares,
        }
    except Exception:
        return {}


async def get_yahoo_quote(ticker: str) -> dict:
    """
    Async wrapper: runs blocking yfinance Ticker.info in a thread pool
    so it does not block the FastAPI event loop.
    """
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, _fetch_yf_info, ticker),
            timeout=15.0
        )
        return result
    except (asyncio.TimeoutError, Exception):
        return {}


async def calculate_valuation(ticker: str, statements: dict) -> dict:
    """
    Fetch live market data via yfinance and compute valuation multiples
    against SEC XBRL financial statement values.
    """
    quote = await get_yahoo_quote(ticker)

    market_cap: float | None = quote.get("market_cap")
    
    # Fallback: compute from price × shares if marketCap missing
    if market_cap is None:
        price  = quote.get("price")
        shares = quote.get("shares")
        if price and shares:
            market_cap = float(price) * float(shares)

    if market_cap is not None:
        market_cap = float(market_cap)

    bal = statements.get("balance_sheet", {})
    inc = statements.get("income_statement", {})

    cash    = bal.get("cash_and_equivalents")
    st_debt = bal.get("short_term_debt") or 0
    lt_debt = bal.get("long_term_debt")  or 0
    total_debt = (
        st_debt + lt_debt
        if bal.get("short_term_debt") is not None or bal.get("long_term_debt") is not None
        else 0
    )

    # Enterprise Value = Market Cap + Total Debt - Cash
    ev: float | None = None
    if market_cap is not None and cash is not None:
        ev = market_cap + total_debt - cash

    net_income = inc.get("net_income")
    equity     = bal.get("shareholder_equity")
    revenue    = inc.get("revenue")
    ebitda     = inc.get("ebitda")

    return {
        "price_to_earnings": safe_div(market_cap, net_income),
        "price_to_book":     safe_div(market_cap, equity),
        "price_to_sales":    safe_div(market_cap, revenue),
        "enterprise_value":  ev,
        "ev_to_ebitda":      safe_div(ev, ebitda),
    }
