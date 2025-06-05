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
    # Dummy-Implementierung: Simuliere das Auslesen der Caption
    # Später hier deine echte Playwright-Logik einfügen
    return {
        "caption": "Beispiel Caption",
        "username": "unbekannt",
        "url": url,
        "date": datetime.datetime.utcnow().isoformat()
    }

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
