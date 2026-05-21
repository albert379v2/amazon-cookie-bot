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


# iniciamos detección de captcha
async def detect_canvas_captcha(page):
    await page.wait_for_timeout(500)

    
    if await page.locator("canvas").count() > 0:
        return True

    text = await page.locator("body").inner_text()
    if "elija todo" in text:
        return True

    if "Resuelve esta adivinanza" in text:
        return True

    

    return False

# captura del captcha


async def capture_captcha(page):

    canvas = page.locator("canvas").first

    await canvas.screenshot(path="captcha.png")

    return "captcha.png"

# click sobre tiles


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

# resolv tiles
# resolv tiles


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

names = ["alexxx", "marrria", "carrrlos",
    "annna", "jooose", "luuuuis", "daaani"]

testC = None


def generate_gmail():
    name = random.choice(names)
    numbers = random.randint(10, 9999)
    return f"{name}{numbers}@mailgrid.shop"


def init_email():
    global testC
    testC = generate_gmail()
    return testC


#detectar captcha
async def detect_captcha_base(page):

    text = (await page.locator("body").inner_text()).lower()

    if "resuelve esta adivinanza para proteger tu cuenta" in text:
        return True

    return False


async def detect_captcha_type(page):

    # ORBIT / ROMPECABEZAS
    if await page.locator("text=Iniciar rompecabezas").count() > 0:
        return "CAPTCHA_ORBIT"

    if await page.locator("text=rompecabezas").count() > 0:
        return "CAPTCHA_ORBIT"

    # CANVAS (TU SISTEMA ACTUAL)
    if await page.locator("canvas").count() > 0:
        return "CAPTCHA_CANVAS"

    return "CAPTCHA_UNKNOWN"
    

# --- RESOLUTOR DE CAPTCHA ---
async def solve_captcha(page):
    try:
        captcha_img = await page.query_selector('img[src*="captcha"]')
        if not captcha_img:
            return False

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
    except:
        pass
    return False

# --- FLUJO DE REGISTRO ---


async def create_amazon():

    init_email()

    email = testC

    async with async_playwright() as p:

        browser = None
        captcha_solved = False
        # otp_handled = False

        try:

            browser = await p.chromium.launch(
                headless=True,
                proxy=PROXY_CONFIG
            )

            context = await browser.new_context()

            page = await context.new_page()
            send_log(f"🚀 Creando: {email}")
            send_log("🔁 antes de goto")
            await page.goto(
                "https://www.amazon.com.mx/ap/signin?openid.return_to=https%3A%2F%2Fwww.amazon.com.mx%2F%3F_encoding%3DUTF8%26ref_%3Dnavm_hdr_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=anywhere_v2_mx&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0",
                wait_until="domcontentloaded",
                timeout=120000
            )
            await page.wait_for_timeout(2000)
            send_log("📍 PAGE READY")
            last_state = None
            captcha_solved = False
            otp_handled = False
            signin_handled = False
            send_log("🔁 ENTER LOOP")

            while True:
                await page.wait_for_timeout(1200)  # 👈 ESTABILIDAD
                state = await detect_state(page)
                send_log(f"STATE RAW => {state}")
                if state == "UNKNOWN":
                    await page.wait_for_timeout(1500)
                    continue

                if state != last_state:
                    send_log(f"STATE => {state}")
                    last_state = state
                    if state != "SIGNIN":
                        signin_handled = False
                    if state != "CAPTCHA_CANVAS":
                        captcha_solved = False
                    if state != "OTP_EMAIL":
                        otp_handled = False

                if state == "LOGIN_PASSWORD":

                    await handle_login_password(page)
                    return

                elif state == "SIGNIN":
                    if signin_handled:
                        await asyncio.sleep(2)
                        continue
                    signin_handled = True
                    send_log("✍️ Insertando correo")
                    await handle_signin(page, testC)
                    await page.wait_for_timeout(2500)
                    #await page.wait_for_load_state("domcontentloaded")
                    await debug(page, "registro")
                    await page.wait_for_timeout(4000)

                elif state == "REGISTER_INTRO":

                    await handle_register_intro(page)

                elif state == "REGISTER_FORM":

                    await handle_register_form(page)



                elif state == "CAPTCHA_DETECTED":
                    await page.wait_for_timeout(1200)
                    send_log("🧩 CAPTCHA DETECTADO")
                    await page.wait_for_timeout(1200)
                    captcha_type = await detect_captcha_type(page)
                    send_log(f"🧠 CAPTCHA TYPE => {captcha_type}")
                    send_log(page.url)
                    if captcha_type == "CAPTCHA_ORBIT":
                        send_log("🌀 Iniciando rompecabezas")
                        try:
                            await page.click("text=Iniciar rompecabezas")
                        except:
                            send_log("❌ No se pudo iniciar rompecabezas")
                            return
                        await page.wait_for_timeout(2000)
                    elif captcha_type == "CAPTCHA_CANVAS":
                        pass
                    else:
                        send_log("⚠️ CAPTCHA desconocido")
                        await debug(page, "captcha_unknown")
                        return
                        ###$
                elif state == "OTP_EMAIL":
                    if otp_handled:
                        await asyncio.sleep(2)
                        continue
                    otp_handled = True
                    send_log(f"📩 Esperando OTP para: {testC}")
                    otp = wait_for_otp(testC)
                    if not otp:
                        send_log("❌ OTP no recibido")
                        return
                    send_log(f"🔢 OTP: {otp}")
                    await page.fill("#cvf-input-code", otp)
                    await page.click("#cvf-submit-otp-button")
                    await page.wait_for_timeout(5000)
                elif state == "OTP_PHONE":
                    send_log("📱 OTP PHONE DETECTADO")
                    send_log(page.url)
                    await debug(page, "otp_phone")
                    return
                elif state == "SUCCESS":
                    send_log("✅ SUCCESS")
                    break
                else:
                    await debug(page, "antes del error")
                    send_log("⚠️ Estado desconocido")
                    text = await page.locator("body").inner_text()
                    send_log(text[:1500])
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
    bot.reply_to(
        message, "ZeuS Bot Online. Usa /crear para una cuenta Amazon mx.")


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
