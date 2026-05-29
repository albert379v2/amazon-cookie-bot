import os
import json
import asyncio
import random
import re
import requests
import base64
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import telebot

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID', 0))
AC_KEY = os.getenv('ANTICAPTCHA_KEY', '')
PROXY_SERVER = os.getenv('PROXY_SERVER', '')
PROXY_USER = os.getenv('PROXY_USER', '')
PROXY_PASS = os.getenv('PROXY_PASS', '')

# === TELEGRAM BOT SETUP ===
bot = telebot.TeleBot(TOKEN) if TOKEN else None

def send_log(msg):
    """Send log message to Telegram and print to console."""
    print(f"[{asyncio.get_event_loop().time():.0f}] {msg}")
    if bot and CHAT_ID:
        try:
            bot.send_message(CHAT_ID, msg)
        except Exception as e:
            print(f"Telegram send failed: {e}")

def send_photo_to_bot(photo_path, caption=""):
    """Send photo to Telegram bot."""
    if bot and CHAT_ID and os.path.exists(photo_path):
        try:
            with open(photo_path, "rb") as photo:
                bot.send_photo(CHAT_ID, photo, caption=caption)
        except Exception as e:
            send_log(f"❌ Photo send failed: {e}")

def send_document_to_bot(doc_path, caption=""):
    """Send document to Telegram bot."""
    if bot and CHAT_ID and os.path.exists(doc_path):
        try:
            with open(doc_path, "rb") as doc:
                bot.send_document(CHAT_ID, doc, caption=caption)
        except Exception as e:
            send_log(f"❌ Document send failed: {e}")

# === EMAIL GENERATION ===
EMAIL_NAMES = ["alexxx", "marrria", "carrrlos", "annna", "jooose", "luuuuis", "daaani"]

def generate_email():
    """Generate random email with mailgrid.shop domain."""
    name = random.choice(EMAIL_NAMES)
    numbers = random.randint(10, 9999)
    return f"{name}{numbers}@mailgrid.shop"

# === CAPTCHA HANDLING ===
captcha_answer = None

def set_captcha_answer(text):
    """Set captcha answer from Telegram message."""
    global captcha_answer
    captcha_answer = text

async def wait_captcha_response(timeout=120):
    """Wait for manual captcha response via Telegram."""
    global captcha_answer
    captcha_answer = None
    start = asyncio.get_event_loop().time()

    while True:
        if captcha_answer:
            response = captcha_answer
            captcha_answer = None
            return response
        if asyncio.get_event_loop().time() - start > timeout:
            return None
        await asyncio.sleep(1)

def parse_tiles(text):
    """Parse tile numbers from text (e.g., '1 3 5' -> [1, 3, 5])."""
    numbers = re.findall(r"\d+", text)
    return [int(x) for x in numbers]

async def detect_canvas_captcha(page):
    """Detect if canvas/Orbit captcha is present."""
    try:
        # Check for Orbit iframe
        orbit = page.locator("#cvf-aamation-challenge-iframe")
        if await orbit.count() > 0:
            send_log("🛰️ Orbit iframe detected")
            return True

        # Check for canvas
        canvas = page.locator("canvas")
        if await canvas.count() > 0:
            send_log("🖼️ Canvas detected")
            return True

        # Check for captcha text
        text = (await page.locator("body").inner_text()).lower()
        if "resuelve esta adivinanza" in text or "elija todo" in text:
            send_log("🧠 Captcha text detected")
            return True

        return False
    except Exception as e:
        send_log(f"❌ Captcha detection error: {e}")
        return False

async def capture_captcha(page, filename="captcha.png"):
    """Capture screenshot of captcha canvas."""
    try:
        canvas = page.locator("canvas").first
        await canvas.screenshot(path=filename)
        return filename
    except Exception as e:
        send_log(f"❌ Captcha capture error: {e}")
        return None

async def click_captcha_tile(page, tile):
    """Click on a specific captcha tile (1-9)."""
    try:
        canvas = page.locator("canvas").first
        box = await canvas.bounding_box()
        if not box:
            send_log("❌ Canvas not found for clicking")
            return

        cell_w = box["width"] / 3
        cell_h = box["height"] / 3
        tile -= 1  # Convert to 0-based
        row = tile // 3
        col = tile % 3

        x = box["x"] + (col * cell_w) + (cell_w / 2)
        y = box["y"] + (row * cell_h) + (cell_h / 2)

        send_log(f"🖱️ Clicking tile {tile + 1}")
        await page.mouse.click(x, y)
    except Exception as e:
        send_log(f"❌ Click tile error: {e}")

async def solve_canvas_captcha(page, tiles):
    """Solve canvas captcha by clicking specified tiles."""
    for tile in tiles:
        await click_captcha_tile(page, tile)
        await asyncio.sleep(0.05)

    # Wait for visual render
    await page.wait_for_timeout(1200)

    # Send preview screenshot
    captcha = page.locator("#captcha-container")
    try:
        await captcha.screenshot(path="captcha_selected.png")
        send_photo_to_bot("captcha_selected.png", caption="✅ Selection preview")
    except:
        pass

    # Click verify
    await page.wait_for_timeout(500)
    await page.click("#amzn-btn-verify-internal")

async def handle_orbit_captcha(page):
    """Handle Orbit/FunCaptcha challenge."""
    send_log("🛰️ Handling Orbit captcha...")
    await page.wait_for_timeout(5000)

    found = False
    for frame in page.frames:
        try:
            buttons = frame.locator("button")
            count = await buttons.count()
            if count > 0:
                texts = await buttons.all_inner_texts()
                send_log(f"🔘 Buttons found: {texts}")

                for i in range(count):
                    btn = buttons.nth(i)
                    text = (await btn.inner_text()).lower()
                    if "rompecabezas" in text or "iniciar" in text or "puzzle" in text:
                        send_log(f"✅ Clicking: {text}")
                        await btn.click(force=True)
                        await page.wait_for_timeout(5000)
                        found = True
                        break
            if found:
                break
        except Exception as e:
            send_log(f"Frame error: {e}")

    return found

async def handle_captcha_challenge(page):
    """Main captcha handler - detects and routes to correct solver."""
    if not await detect_canvas_captcha(page):
        send_log("✅ No captcha detected")
        return True

    # Check for Orbit iframe
    orbit_iframe = page.locator("#cvf-aamation-challenge-iframe")
    if await orbit_iframe.count() > 0:
        return await handle_orbit_captcha(page)

    # Handle canvas captcha (manual via Telegram)
    send_log("🖼️ Canvas captcha - sending to Telegram...")
    path = await capture_captcha(page)
    if path:
        send_photo_to_bot(path, caption="Responde con tiles.\nEjemplo: 1 3 5")

    response = await wait_captcha_response()
    if not response:
        send_log("❌ Captcha timeout")
        return False

    tiles = parse_tiles(response)
    send_log(f"🎯 Tiles received: {tiles}")
    await solve_canvas_captcha(page, tiles)
    send_log("✅ Captcha solved")
    return True

# === IMAGE CAPTCHA SOLVER (AntiCaptcha) ===
async def solve_image_captcha(page):
    """Solve traditional image captcha using AntiCaptcha."""
    if not AC_KEY:
        send_log("⚠️ AntiCaptcha key not configured")
        return False

    try:
        captcha_img = await page.query_selector('img[src*="captcha"]')
        if not captcha_img:
            return False

        img_url = await captcha_img.get_attribute("src")
        img_res = requests.get(img_url, timeout=35)
        img_b64 = base64.b64encode(img_res.content).decode('utf-8')

        # Create task
        task = requests.post("https://api.anti-captcha.com/createTask", json={
            "clientKey": AC_KEY,
            "task": {"type": "ImageToTextTask", "body": img_b64}
        }).json()

        task_id = task.get("taskId")
        if not task_id:
            send_log("❌ AntiCaptcha task creation failed")
            return False

        # Wait for result
        for _ in range(15):
            await asyncio.sleep(3)
            res = requests.post("https://api.anti-captcha.com/getTaskResult", json={
                "clientKey": AC_KEY,
                "taskId": task_id
            }).json()

            if res.get("status") == "ready":
                text = res["solution"]["text"]
                send_log(f"✅ Captcha solved: `{text}`")
                await page.fill("#captchacharacters", text)
                await page.press("#captchacharacters", "Enter")
                return True

        send_log("❌ AntiCaptcha timeout")
        return False
    except Exception as e:
        send_log(f"❌ Image captcha error: {e}")
        return False

# === BROWSER SETUP ===
def get_proxy_config():
    """Build proxy config from environment variables."""
    if not PROXY_SERVER:
        return None

    proxy = {"server": PROXY_SERVER}
    if PROXY_USER and PROXY_PASS:
        proxy["username"] = PROXY_USER
        proxy["password"] = PROXY_PASS
    return proxy

async def launch_browser():
    """Launch browser with optional proxy."""
    proxy = get_proxy_config()
    launch_args = {"headless": True}
    if proxy:
        launch_args["proxy"] = proxy
        send_log(f"🌐 Using proxy: {PROXY_SERVER}")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(**launch_args)
    return playwright, browser

async def new_page(browser):
    """Create new browser context and page."""
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"
    )
    page = await context.new_page()
    return context, page

# === AMAZON REGISTRATION FLOW ===
AMAZON_LOGIN_URL = (
    "https://www.amazon.com.mx/ap/signin?"
    "openid.return_to=https%3A%2F%2Fwww.amazon.com.mx%2F%3F_encoding%3DUTF8%26ref_%3Dnavm_hdr_signin&"
    "openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&"
    "openid.assoc_handle=anywhere_v2_mx&"
    "openid.mode=checkid_setup&"
    "openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&"
    "openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
)

async def navigate_to_amazon(page):
    """Navigate to Amazon login page."""
    send_log("🚀 Navigating to Amazon MX...")
    await page.goto(AMAZON_LOGIN_URL, wait_until="domcontentloaded", timeout=120000)
    await page.wait_for_timeout(2000)
    send_log(f"📍 URL: {page.url}")

async def enter_email(page, email):
    """Enter email and proceed."""
    send_log(f"📝 Entering email: {email}")
    await page.fill("#ap_email_login", email)
    await page.click("#continue")
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(2000)

async def confirm_registration(page):
    """Click 'Create account' button."""
    send_log("🔘 Confirming registration...")
    await page.click("#intention-submit-button")
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(2000)

async def fill_registration_form(page):
    """Fill name and password fields."""
    send_log("📝 Filling registration form...")
    await page.fill("#ap_customer_name", "Jhonatan Aldama")
    await page.fill("#ap_password", "Admin.2026.!")
    await page.wait_for_timeout(500)

async def submit_registration(page):
    """Submit registration form."""
    send_log("📤 Submitting registration...")
    await page.click("#continue")
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(2000)

async def wait_for_otp_email(email):
    """Wait for OTP from Gmail reader."""
    send_log(f"📩 Waiting for OTP: {email}")
    # Import here to avoid circular dependency
    try:
        from gmail.gmail_reader import wait_for_otp
        otp = wait_for_otp(email)
        if otp:
            send_log(f"🔢 OTP received: `{otp}`")
            return otp
    except ImportError:
        send_log("⚠️ Gmail reader not available")
    return None

async def enter_otp(page, otp):
    """Enter OTP and verify."""
    send_log("🔐 Entering OTP...")
    await page.fill("#cvf-input-code", otp)
    await page.wait_for_timeout(3000)
    await page.click("#cvf-submit-otp-button")
    await page.wait_for_timeout(11000)

async def save_session(context, email):
    """Save cookies to file and send to Telegram."""
    cookies = await context.cookies()
    filename = f"session_{email.replace('@', '_').replace('.', '_')}.json"

    with open(filename, "w") as f:
        json.dump(cookies, f, indent=2)

    send_document_to_bot(filename, caption=f"✅ Amazon account created: {email}")
    send_log("💾 Session saved")
    return filename

# === MAIN REGISTRATION ===
async def create_amazon_account():
    """Main account creation flow."""
    email = generate_email()
    send_log(f"🎯 Target email: {email}")

    playwright = None
    browser = None

    try:
        # Launch browser
        playwright, browser = await launch_browser()
        context, page = await new_page(browser)

        # Step 1: Navigate to Amazon
        await navigate_to_amazon(page)

        # Step 2: Solve initial captcha if present
        await solve_image_captcha(page)

        # Step 3: Enter email
        await enter_email(page, email)

        # Step 4: Confirm registration
        await confirm_registration(page)

        # Step 5: Fill form
        await fill_registration_form(page)
        await submit_registration(page)

        # Step 6: Handle post-submit captcha
        await asyncio.sleep(5)
        await solve_image_captcha(page)

        # Step 7: Wait for and solve canvas/Orbit captcha
        await page.wait_for_timeout(8000)
        await handle_captcha_challenge(page)

        # Step 8: Wait for OTP
        otp = await wait_for_otp_email(email)
        if not otp:
            send_log("❌ OTP not received")
            return False

        # Step 9: Enter OTP
        await enter_otp(page, otp)

        # Step 10: Save session
        await save_session(context, email)
        send_log("✅ Account created successfully!")
        return True

    except Exception as e:
        send_log(f"❌ Error: {str(e)}")
        import traceback
        send_log(f"Trace: {traceback.format_exc()[:500]}")
        return False
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

# === TELEGRAM BOT HANDLERS ===
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "🤖 Amazon Bot Online\nUse /crear to start")

@bot.message_handler(commands=['crear'])
def run_cmd(message):
    bot.reply_to(message, "⚙️ Starting account creation...")
    asyncio.run(create_amazon_account())

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    """Handle any text message as captcha answer."""
    set_captcha_answer(message.text)

# === ENTRY POINT ===
if __name__ == "__main__":
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set! Create .env file.")
        exit(1)

    send_log("🔥 Bot started successfully")
    bot.infinity_polling()
