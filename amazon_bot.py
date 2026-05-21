import time
import os
import json
import asyncio
import random
import re
import telebot
import requests
import base64
import time
from playwright.async_api import async_playwright
from config import *
from utils import set_bot, safe_name, send_log, send_screenshot, take_screenshot, debug
from gmail.gmail_reader import wait_for_otp
from states import detect_state
from handlers.login import (
    handle_login_password,
    handle_signin
)
from handlers.register import (
    handle_register_intro,
    handle_register_form
)

# === CONFIGURACIÓN ===

bot = telebot.TeleBot(TOKEN)
set_bot(bot)


#iniciamos detección de captcha
async def detect_canvas_captcha(page):

    text = await page.locator("body").inner_text()

    if "Elija todo" in text:
        return True

    if "Resuelve esta adivinanza" in text:
        return True

    if await page.locator("canvas").count() > 0:
        return True

    return False

#captura del captcha
async def capture_captcha(page):

    canvas = page.locator("canvas").first

    await canvas.screenshot(path="captcha.png")

    return "captcha.png"

#click sobre tiles

async def click_captcha_tile(page, tile):

    canvas = page.locator("canvas").first

    box = await canvas.bounding_box()

    if not box:
        send_log("Canvas no encontrado")
        return

    cell_w = box["width"] / 3
    cell_h = box["height"] / 3

    tile -= 1

    row = tile // 3
    col = tile % 3

    x = box["x"] + (col * cell_w) + (cell_w / 2)
    y = box["y"] + (row * cell_h) + (cell_h / 2)

    send_log(f"Click tile {tile+1}")

    await page.mouse.click(x, y)

#resolv tiles
#resolv tiles
async def solve_canvas_captcha(page, tiles):

    for tile in tiles:

        await click_captcha_tile(page, tile)

        await asyncio.sleep(0.05)

    # Esperar render visual REAL del canvas
    await page.wait_for_timeout(1200)

    # Screenshot final
    captcha = page.locator("#captcha-container")

    await captcha.screenshot(path="captcha_selected.png")

    with open("captcha_selected.png", "rb") as photo:
        bot.send_photo(
            CHAT_ID,
            photo,
            caption="✅ Preview selección"
        )

    # Pequeña pausa antes de verify
    await page.wait_for_timeout(500)

    # Verify
    await page.click("#amzn-btn-verify-internal")

###
def parse_tiles(text):

    numbers = re.findall(r"\d+", text)

    return [int(x) for x in numbers]


captcha_answer = None



async def wait_captcha_response(timeout=120):

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



# --- MANEJO DE CORREO (MAIL.TM API) ---

# --- MANEJO DE CORREO ---

names = ["alexxx", "marrria", "carrrlos", "annna", "jooose", "luuuuis", "daaani"]

testC = None

def generate_gmail():
    name = random.choice(names)
    numbers = random.randint(10, 9999)
    return f"{name}{numbers}@mailgrid.shop"


def init_email():
    global testC
    testC = generate_gmail()
    return testC


    
# --- RESOLUTOR DE CAPTCHA ---
async def solve_captcha(page):
    try:
        captcha_img = await page.query_selector('img[src*="captcha"]')
        if not captcha_img: return False
        
        img_url = await captcha_img.get_attribute("src")
        img_res = requests.get(img_url, timeout=35)
        img_b64 = base64.b64encode(img_res.content).decode('utf-8')

        task = requests.post("https://api.anti-captcha.com/createTask", json={
            "clientKey": AC_KEY, "task": {"type": "ImageToTextTask", "body": img_b64}
        }).json()
        
        task_id = task.get("taskId")
        for _ in range(15):
            await asyncio.sleep(3)
            res = requests.post("https://api.anti-captcha.com/getTaskResult", json={
                "clientKey": AC_KEY, "taskId": task_id
            }).json()
            if res.get("status") == "ready":
                text = res["solution"]["text"]
                send_log(f"✅ Captcha: `{text}`")
                await page.fill("#captchacharacters", text)
                await page.press("#captchacharacters", "Enter")
                return True
    except: pass
    return False

# --- FLUJO DE REGISTRO ---
async def create_amazon():

    init_email()

    email = testC

    async with async_playwright() as p:

        browser = None
        captcha_solved = False

        try:

            browser = await p.chromium.launch(
                headless=True,
                proxy=PROXY_CONFIG
            )

            context = await browser.new_context()

            page = await context.new_page()
            send_log(f"🚀 Creando: {email}")
            await page.goto(
                "https://www.amazon.com.mx/ap/signin?openid.return_to=https%3A%2F%2Fwww.amazon.com.mx%2F%3F_encoding%3DUTF8%26ref_%3Dnavm_hdr_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=anywhere_v2_mx&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0",
                wait_until="domcontentloaded",
                timeout=120000
            )
            last_state = None
            captcha_solved = False

            while True:

                state = await detect_state(page)

                if state != last_state:
                    send_log(f"STATE => {state}")
                    last_state = state
                    if state != "CAPTCHA_CANVAS":
                        captcha_solved = False

                if state == "LOGIN_PASSWORD":

                    await handle_login_password(page)
                    return

                elif state == "SIGNIN":
                    await handle_signin(page, testC)
                    await page.wait_for_timeout(3000)

                elif state == "REGISTER_INTRO":

                    await handle_register_intro(page)

                elif state == "REGISTER_FORM":

                    await handle_register_form(page)

                elif state == "CAPTCHA_CANVAS":
                    if captcha_solved:
                        await asyncio.sleep(2)
                        continue
                    captcha_solved = True
                    send_log("CAPTCHA DETECTADO")
                    path = await capture_captcha(page)
                    with open(path, "rb") as photo:
                        bot.send_photo(CHAT_ID, photo)
                    response = await wait_captcha_response()
                    if not response:
                        send_log("Timeout captcha")
                        return
                    tiles = parse_tiles(response)
                    await solve_canvas_captcha(page, tiles)
                    send_log("Captcha enviado")
                    
                    try:
                        await page.wait_for_function("""
                        () => !document.body.innerText.includes('Elija todo')
                        """, timeout=10000)
                    except:
                        send_log("Captcha sigue presente")
                        await page.wait_for_timeout(3000)

                elif state == "OTP_EMAIL":

                    send_log("OTP DETECTADO")

                elif state == "SUCCESS":

                    send_log("✅ SUCCESS")
                    break

                else:
                    send_log("⚠️ Estado desconocido")
                    text = await page.locator("body").inner_text()
                    send_log(text[:1500])
                    await page.wait_for_timeout(7000)
                    await debug(page, "unknown_state")
                    return

                await asyncio.sleep(1)

        except Exception as e:

            send_log(f"⚠️ Error: {str(e)}")

        finally:

            if browser:

                await browser.close()


# --- BOT INTERFACE ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "ZeuS Bot Online. Usa /crear para una cuenta Amazon mx.")

@bot.message_handler(commands=['crear'])
def run_cmd(message):
    bot.reply_to(message, "⚙️ Iniciando proceso1...")
    asyncio.run(create_amazon())


@bot.message_handler(func=lambda m: True)
def handle_message(message):

    global captcha_answer

    captcha_answer = message.text

if __name__ == "__main__":
    send_log("🔥 Bot iniciado correctamente en Railway")
    bot.infinity_polling()
