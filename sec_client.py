import httpx
import logging
from fastapi import HTTPException
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "SEC Filing Analytics API your.email@example.com",
    "Accept-Encoding": "gzip, deflate",
}

class SECClient:
    def __init__(self):
        self.client = httpx.AsyncClient(headers=HEADERS, timeout=30.0)
        self.cache: Dict[str, Any] = {}
        self.rate_limit_lock = asyncio.Lock()
    
    async def get(self, url: str) -> dict:
        if url in self.cache:
            return self.cache[url]
        
        async with self.rate_limit_lock:
            await asyncio.sleep(0.12)
            try:
                r = await self.client.get(url, follow_redirects=True)
                if r.status_code == 404:
                    raise HTTPException(status_code=404, detail="Not found in SEC database.")
                if r.status_code == 403:
                    raise HTTPException(status_code=403, detail="Forbidden - Rate limit or User-Agent rejection.")
                r.raise_for_status()
                data = r.json()
                self.cache[url] = data
                return data
            except httpx.HTTPError as e:
                logger.error(f"HTTPError fetching {url}: {e}")
                raise HTTPException(status_code=502, detail="Error communicating with SEC API")
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal Server Error")
    
    async def close(self):
        await self.client.aclose()

sec_client = SECClient()
