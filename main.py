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

            # Caption auslesen
            caption = await page.locator("xpath=//div[contains(@class, 'x1lliihq')]//span").first.text_content()
            caption = caption.strip() if caption else ""

            # Username auslesen mit Fehlerbehandlung
            try:
                username = await page.locator("xpath=//a[contains(@href, '/reel/')]/../../preceding-sibling::div//span").first.text_content()
                username = username.strip() if username else "unbekannt"
            except:
                username = "unbekannt"

            return {
                "caption": caption,
                "username": username,
                "url": url,
                "date": datetime.datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise HTTPExce
