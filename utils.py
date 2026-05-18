import os
import telebot
from config import CHAT_ID

DEBUG_DIR = "debug"
os.makedirs(DEBUG_DIR, exist_ok=True)

# ⚠️ IMPORTANTE: el bot se crea en main.py, aquí NO se redefine
bot = None


def set_bot(instance):
    global bot
    bot = instance

###1
def safe_name(name: str) -> str:
    return (
        name.replace("/", "_")
            .replace(" ", "_")
            .replace(":", "_")
            .replace("?", "_")
            .replace("=", "_")
    )


async def take_screenshot(page, step: str):
    path = os.path.join(DEBUG_DIR, f"{safe_name(step)}.png")

    await page.screenshot(
        path=path,
        full_page=True
    )

    return path



def send_screenshot(path: str, caption: str):
    with open(path, "rb") as img:
        bot.send_photo(CHAT_ID, img, caption=caption)

async def debug(page, step: str):
    try:
        path = await take_screenshot(page, step)
        send_screenshot(path, f"📸 {step}")
    except Exception as e:
        print(f"Screenshot error: {e}")


def send_log(msg):
    print(msg)
    try: bot.send_message(CHAT_ID, f"🤖 {msg}", parse_mode="Markdown")
    except: pass
