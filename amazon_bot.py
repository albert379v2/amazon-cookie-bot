import os
import asyncio
import telebot
from playwright.async_api import async_playwright

# ======================
# CONFIG
# ======================
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(TOKEN)

# ======================
# LOG
# ======================
def send_log(msg):
    print(msg)
    try:
        bot.send_message(CHAT_ID, f"🤖 {msg}")
    except:
        pass

# ======================
# SCREENSHOT (ESTABLE)
# ======================
def send_screenshot(page, name):
    try:
        path = f"{name}.png"
        page.screenshot(path=path, full_page=True)

        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=name)

    except Exception as e:
        send_log(f"Screenshot error: {e}")

# ======================
# CORE FLOW (BASE)
# ======================
async def run():
    send_log("🚀 Iniciando flujo limpio")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        send_log("🌐 Abriendo página")
        await page.goto("https://google.com")

        send_screenshot(page, "step_1")

        send_log("✅ Paso 1 completo")

        await browser.close()

# ======================
# START
# ======================
if __name__ == "__main__":
    asyncio.run(run())
