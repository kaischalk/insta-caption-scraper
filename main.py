from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from playwright.async_api import async_playwright
import datetime

app = FastAPI()

class LoginData(BaseModel):
    username: str
    password: str

class ExtractData(BaseModel):
    link: str
    cookies: dict
    kategorie: str = ""

@app.post("/login")
async def login(data: LoginData):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto("https://www.instagram.com/accounts/login/")
            await page.wait_for_selector("input[name='username']")

            await page.fill("input[name='username']", data.username)
            await page.fill("input[name='password']", data.password)
            await page.click("button[type='submit']")

            await page.wait_for_timeout(5000)

            if "challenge" in page.url or "two_factor" in page.url:
                raise HTTPException(status_code=401, detail="2FA oder Challenge notwendig")

            cookies = await context.cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}

            return {
                "success": True,
                "cookies": cookie_dict,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        finally:
            await browser.close()

@app.post("/extract")
async def extract(data: ExtractData):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        cookie_list = [
            {"name": k, "value": v, "domain": ".instagram.com", "path": "/"}
            for k, v in data.cookies.items()
        ]
        await context.add_cookies(cookie_list)

        page = await context.new_page()

        try:
            await page.goto(data.link)
            await page.wait_for_selector("article")

            caption_elem = await page.query_selector("xpath=//div[contains(@class, 'x1lliihq')]//span")
            caption = await caption_elem.text_content() if caption_elem else ""

            user_elem = await page.query_selector("xpath=//header//a")
            username = await user_elem.text_content() if user_elem else "unbekannt"

            return {
                "caption": caption.strip(),
                "username": username.strip(),
                "url": data.link,
                "date": datetime.datetime.utcnow().isoformat(),
                "kategorie": data.kategorie
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        finally:
            await browser.close()
