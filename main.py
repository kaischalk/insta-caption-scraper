
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from playwright.async_api import async_playwright
import datetime
import traceback
import logging

print(">>>>> DIESE VERSION WIRD VERWENDET <<<<<")

logging.basicConfig(
    filename="extractor.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

app = FastAPI()

class LoginData(BaseModel):
    username: str
    password: str

class ExtractData(BaseModel):
    link: str
    cookies: dict
    kategorie: str = ""

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "trace": traceback.format_exc()
        },
    )

@app.get("/debug")
async def debug_playwright():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://www.instagram.com/", timeout=15000)
            content = await page.content()
            await browser.close()
            return {"success": True, "html_length": len(content)}
    except Exception as e:
        logging.error(f"Debug failed: {e}")
        return {"success": False, "error": str(e)}

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
                logging.warning("Login failed due to 2FA or challenge")
                raise HTTPException(status_code=401, detail="2FA oder Challenge notwendig")
            cookies = await context.cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            logging.info(f"Login successful for user: {data.username}")
            return {
                "success": True,
                "cookies": cookie_dict,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        except Exception as e:
            logging.error(f"Login error for user {data.username}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            await browser.close()

@app.post("/extract")
async def extract(data: ExtractData):
    logging.info(f"Starting extract for {data.link}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies([
            {"name": k, "value": v, "domain": ".instagram.com", "path": "/"}
            for k, v in data.cookies.items()
        ])
        page = await context.new_page()
        try:
            await page.goto(data.link)
            await page.wait_for_selector("article", timeout=10000)

            caption_elem = await page.query_selector("xpath=//div[contains(@class, 'x1lliihq')]//span")
            user_elem = await page.query_selector("xpath=//header//a")

            caption = await caption_elem.text_content() if caption_elem else None
            username = await user_elem.text_content() if user_elem else None

            if not caption or not username:
                logging.warning(f"Extraction failed: no content found at {data.link}")
                raise HTTPException(
                    status_code=422,
                    detail="Caption oder Username konnte nicht extrahiert werden. Prüfe den Link oder Login."
                )

            logging.info(f"Extract successful: {username}, {data.kategorie}")
            return {
                "caption": caption.strip(),
                "username": username.strip(),
                "url": data.link,
                "date": datetime.datetime.utcnow().isoformat(),
                "kategorie": data.kategorie
            }

        except Exception as e:
            logging.error(f"Error during extraction for {data.link}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            await browser.close()
