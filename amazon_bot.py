import os
import asyncio
import random
import telebot
from playwright.async_api import async_playwright

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(TOKEN)

# =========================
# DEBUG DIR SAFE (RAILWAY OK)
# =========================
DEBUG_DIR = os.path.join(os.getcwd(), "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)


# =========================
# UTILS
# =========================
def safe_name(name: str) -> str:
    return (
        name.replace("/", "_")
        .replace(" ", "_")
        .replace(":", "_")
        .replace("(", "_")
        .replace(")", "_")
    )


def send_log(msg: str):
    print(msg)
    try:
        bot.send_message(CHAT_ID, f"🤖 {msg}")
    except:
        pass


def send_screenshot_file(path: str, caption: str):
    try:
        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=caption)
    except Exception as e:
        send_log(f"❌ send_photo error: {e}")


# =========================
# DEBUG CORE
# =========================
async def debug_screenshot(page, step: str):
    try:
        path = os.path.join(DEBUG_DIR, f"{safe_name(step)}.png")
        await page.screenshot(path=path, full_page=True)
        send_screenshot_file(path, f"📸 {step}")
    except Exception as e:
        send_log(f"❌ Screenshot error: {e}")


async def debug_snapshot(page, step: str):
    try:
        # HTML dump correcto (NO coroutine error)
        html = await page.content()

        html_path = os.path.join(DEBUG_DIR, f"{safe_name(step)}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        send_log(f"🌐 STEP: {step}")
        send_log(f"🔗 URL: {page.url}")

        await debug_screenshot(page, step)

    except Exception as e:
        send_log(f"❌ Snapshot error: {e}")


# =========================
# MAIL MOCK (placeholder estable)
# =========================
class MailTM:
    def get_account(self):
        return f"zeus{random.randint(1000,9999)}@mail.tm"

    async def wait_for_otp(self):
        send_log("📩 Esperando OTP...")
        await asyncio.sleep(5)
        return "123456"


# =========================
# STATE MACHINE
# =========================
STATE_INIT = "INIT"
STATE_OPEN = "OPEN"
STATE_EMAIL = "EMAIL"
STATE_ROUTE = "ROUTE"
STATE_REGISTER = "REGISTER"
STATE_LOGIN = "LOGIN"
STATE_OTP = "OTP"
STATE_DONE = "DONE"
STATE_ERROR = "ERROR"


class AmazonStateMachine:
    def __init__(self, page, mail):
        self.page = page
        self.mail = mail
        self.state = STATE_INIT
        self.email = None

    def set_state(self, state):
        self.state = state
        send_log(f"🔁 STATE → {state}")

    async def step(self, name, action):
        try:
            send_log(f"➡️ STEP: {name}")

            await debug_snapshot(self.page, name)

            result = await action()

            await debug_snapshot(self.page, f"{name}_after")

            return result

        except Exception as e:
            send_log(f"❌ ERROR STEP {name}: {e}")
            await debug_snapshot(self.page, f"{name}_error")
            self.set_state(STATE_ERROR)
            raise


    # =====================
    async def open(self):
        self.set_state(STATE_OPEN)

        await self.step(
            "goto",
            lambda: self.page.goto(
                "https://www.amazon.com.mx/ap/signin",
                wait_until="domcontentloaded",
                timeout=120000
            )
        )


    # =====================
    async def email(self):
        self.set_state(STATE_EMAIL)

        self.email = self.mail.get_account()

        await self.step(
            "fill_email",
            lambda: self.page.fill("#ap_email, #ap_email_login", self.email)
        )

        await self.step(
            "continue",
            lambda: self.page.click("#continue")
        )


    # =====================
    async def route(self):
        self.set_state(STATE_ROUTE)

        await self.page.wait_for_timeout(3000)

        if await self.page.locator("#ap_password").count() > 0:
            self.set_state(STATE_LOGIN)

        elif await self.page.locator("#ap_customer_name").count() > 0:
            self.set_state(STATE_REGISTER)

        else:
            self.set_state(STATE_ERROR)
            send_log("⚠️ FLOW UNKNOWN")


    # =====================
    async def register(self):
        if self.state != STATE_REGISTER:
            return

        await self.step(
            "name",
            lambda: self.page.fill("#ap_customer_name", f"User {random.randint(10,99)}")
        )

        await self.step(
            "password",
            lambda: self.page.fill("#ap_password", "Admin.2026.!")
        )

        await self.step(
            "submit",
            lambda: self.page.click("#auth-continue")
        )


    # =====================
    async def otp(self):
        self.set_state(STATE_OTP)

        otp = await self.mail.wait_for_otp()

        if not otp:
            self.set_state(STATE_ERROR)
            send_log("❌ OTP FAIL")
            return

        await self.step(
            "otp_fill",
            lambda: self.page.fill("input[name='code']", otp)
        )

        await self.step(
            "otp_submit",
            lambda: self.page.click("#cvf-submit-otp-button")
        )

        self.set_state(STATE_DONE)
        send_log("✅ DONE")


# =========================
# RUNNER
# =========================
async def run():
    send_log("🚀 START SYSTEM")

    mail = MailTM()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        sm = AmazonStateMachine(page, mail)

        try:
            await sm.open()
            await sm.email()
            await sm.route()

            if sm.state == STATE_REGISTER:
                await sm.register()

            await sm.otp()

        except Exception as e:
            send_log(f"💥 FATAL: {e}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
