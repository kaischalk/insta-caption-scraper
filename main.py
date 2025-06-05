from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import datetime
import re

from playwright.async_api import async_playwright

app = FastAPI()

class ReelLinkRequest(BaseModel):
    links: List[str]

async def extract_instagram_caption(url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(url, timeout=15000)
            await page.wait_for_timeout(3000)  # kurz warten, bis Seite lädt

            caption = await page.locator("xpath=//div[contains(@class, 'x1lliihq')]//span").first.text_content()
            username = await page.locator("xpath=//a[contains(@href, '/reel/')]/../../preceding-sibling::div//span").first.text_content()

            return {
                "caption": caption.strip() if caption else "",
                "username": username.strip() if username else "",
                "url": url,
                "date": datetime.datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fehler beim Verarbeiten von {url}: {str(e)}")
        finally:
            await browser.close()

@app.post("/extract")
async def extract_captions(request: ReelLinkRequest):
    results = []

    for link in request.links:
        if not re.match(r"https://www.instagram.com/reel/", link):
            continue
        try:
            data = await extract_instagram_caption(link)
            results.append(data)
        except HTTPException as e:
            results.append({"url": link, "error": e.detail})

    return {"results": results}
