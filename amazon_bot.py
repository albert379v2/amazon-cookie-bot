import os
import asyncio
import random
import re
import json
import telebot
import requests
from playwright.async_api import async_playwright

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
AC_KEY = os.getenv("AC_KEY")

bot = telebot.TeleBot(TOKEN)


DEBUG_DIR = "/tmp/debug"
os.makedirs(DEBUG_DIR, exist_ok=True)

async def debug_screenshot(page, step):
    try:
        path = os.path.join(DEBUG_DIR, f"{safe_name(step)}.png")

        await page.screenshot(path=path, full_page=True)

        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=f"📸 {step}")

    except Exception as e:
        send_log(f"Screenshot error: {e}")

# =========================
# LOG SYSTEM
# =========================
def send_log(msg):
    print(msg)
    try:
        bot.send_message(CHAT_ID, f"🤖 {msg}")
    except:
        pass

# =========================
# DEBUG SYSTEM
# =========================
def safe_name(name):
    return name.replace("/", "_").replace(" ", "_").replace(":", "_")

def debug_screenshot(page, name):
    try:
        path = os.path.join(DEBUG_DIR, f"{safe_name(name)}.png")
        page.screenshot(path=path, full_page=True)

        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=f"📸 {name}")

    except Exception as e:
        send_log(f"Screenshot error: {e}")

async def debug_snapshot(page, step):
    try:
        html_path = os.path.join(DEBUG_DIR, f"{safe_name(step)}.html")

        html = await page.content()

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        send_log(f"🌐 STEP: {step}")
        send_log(f"🔗 URL: {page.url}")

        await debug_screenshot(page, step)

    except Exception as e:
        send_log(f"Snapshot error: {e}")

# =========================
# MAIL (simplificado placeholder)
# =========================
class MailTM:
    def get_account(self):
        domain = "mail.tm"
        return f"zeus{random.randint(1000,9999)}@{domain}"

    async def wait_for_otp(self):
        send_log("📩 Esperando OTP...")
        await asyncio.sleep(10)
        return "123456"

# =========================
# STATE MACHINE
# =========================
STATE_INIT = "INIT"
STATE_OPEN = "OPEN"
STATE_CLAIM = "CLAIM"
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

    def set_state(self, s):
        self.state = s
        send_log(f"🔁 STATE → {s}")

    async def step(self, name, action):
    try:
        send_log(f"➡️ STEP {name}")

        await debug_snapshot(self.page, name)

        result = await action()

        await debug_snapshot(self.page, f"{name}_after")

        return result

    except Exception as e:
        send_log(f"❌ ERROR {name}: {e}")
        await debug_snapshot(self.page, f"{name}_ERROR")
        self.set_state(STATE_ERROR)
        raise e

    # =====================
    async def open(self):
        self.set_state(STATE_OPEN)

        await self.step("goto", lambda: self.page.goto(
            "https://www.amazon.com.mx/ap/signin",
            wait_until="domcontentloaded",
            timeout=120000
        ))

    # =====================
    async def claim(self):
        self.set_state(STATE_CLAIM)

        if "/ax/claim" in self.page.url:
            send_log("⏳ Claim routing detectado")

        await self.page.wait_for_timeout(3000)

    # =====================
    async def email_step(self):
        self.set_state(STATE_EMAIL)

        self.email = self.mail.get_account()

        await self.step("fill_email", lambda: self.page.fill(
            "#ap_email_login, #ap_email",
            self.email
        ))

        await self.step("continue", lambda: self.page.click("#continue"))

    # =====================
    async def route(self):
        self.set_state(STATE_ROUTE)

        await self.page.wait_for_timeout(3000)

        if await self.page.locator("#ap_password").count() > 0:
            self.set_state(STATE_LOGIN)
            send_log("🔐 LOGIN")

        elif await self.page.locator("#ap_customer_name").count() > 0:
            self.set_state(STATE_REGISTER)
            send_log("🆕 REGISTER")

        else:
            self.set_state(STATE_ERROR)
            send_log("⚠️ FLOW UNKNOWN")

    # =====================
    async def register(self):
        if self.state != STATE_REGISTER:
            return

        await self.step("name", lambda: self.page.fill(
            "#ap_customer_name",
            f"User {random.randint(10,99)}"
        ))

        await self.step("pass", lambda: self.page.fill(
            "#ap_password",
            "Admin.2026.!"
        ))

        await self.step("submit", lambda: self.page.click("#auth-continue"))

    # =====================
    async def otp(self):
        self.set_state(STATE_OTP)

        otp = await self.mail.wait_for_otp()

        if not otp:
            send_log("❌ OTP FAIL")
            self.set_state(STATE_ERROR)
            return

        await self.step("otp_fill", lambda: self.page.fill(
            "input[name='code']",
            otp
        ))

        await self.step("otp_submit", lambda: self.page.click(
            "#cvf-submit-otp-button"
        ))

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
            await sm.claim()
            await sm.email_step()
            await sm.route()

            if sm.state == STATE_REGISTER:
                await sm.register()

            await sm.otp()

        except Exception as e:
            send_log(f"💥 FATAL: {e}")

        await browser.close()


# =========================
# START
# =========================
if __name__ == "__main__":
    asyncio.run(run())
