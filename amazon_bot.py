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


def extract_canvas_question(text):

    lines = text.splitlines()

    for line in lines:

        if "Elija todo" in line:
            return line

        if "Resuelve esta adivinanza" in line:
            return line

    return "Captcha detectado"

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
    send_log(testC)
    email = testC
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, proxy=PROXY_CONFIG)
            async def new_clean_page():
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"
                )
                page = await context.new_page()
                return context, page

            # ✅ AQUÍ SE CREA REALMENTE page
            context, page = await new_clean_page()

            send_log(f"🚀 Creando: `{email}`")
            send_log("E7 - Entrando a Amazon")
            await debug(page, "0create_mail")
            await page.goto(
    "https://www.amazon.com.mx/ap/signin?openid.return_to=https%3A%2F%2Fwww.amazon.com.mx%2F%3F_encoding%3DUTF8%26ref_%3Dnavm_hdr_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=anywhere_v2_mx&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0",
    wait_until="domcontentloaded",
    timeout=120000
)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            
            send_log(page.url)
            await debug(page, "amazon_link")

            send_log("E8 - Amazon cargó")
            await solve_captcha(page)
            send_log("E9 - tiene captcha 1")
            
            send_log("F1")
            await page.fill("#ap_email_login", testC)
            await debug(page, "01_insert_email")
            send_log("F2")
            await page.click("#continue")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            await debug(page, "01_click_continue")
            send_log("F2 vontinue1")
            await page.click("#intention-submit-button")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            await debug(page, "01_click_comfirregister")
            send_log("Fllemar datos")
            await page.fill("#ap_customer_name", "Jhonatan aldama")            
            send_log("F3")
            await page.fill("#ap_password", "Admin.2026.!")
            await debug(page, "01_formulario")
            send_log("F4")
            ##await page.fill("#ap_password_check", "Admin.2026.!")
            send_log("F5 inicia click")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            await page.click("#continue")
            ##await page.click("#continue")
            send_log("F6 click exitoso")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            await debug(page, "01_click_registrtage")
            send_log("E8 - se lleno formulario")
            send_log(page.url)
            await asyncio.sleep(5)
            await solve_captcha(page)
            send_log(page.url)
            send_log("E8 - captcha2")
            await debug(page, "captcha_final")
            await page.wait_for_load_state("domcontentloaded")
            if await detect_canvas_captcha(page):
                send_log("CAPTCHA CANVAS DETECTADO")
                await debug(page, "canvas_detected")
                path = await capture_captcha(page)
                text = await page.locator("body").inner_text()
                question = extract_canvas_question(text)
                bot.send_photo(CHAT_ID, photo,
                               caption=question)
                with open(path, "rb") as photo:
                    bot.send_photo(CHAT_ID, photo)
                    bot.send_message(
                    CHAT_ID,
                    "Responde con las casillas.\nEjemplo: 2 5 8"
                )
                    response = await wait_captcha_response()
                    if not response:
                        send_log("Timeout captcha")
                        return
                    tiles = parse_tiles(response)
                    send_log(f"Tiles: {tiles}")
                    await solve_canvas_captcha(page, tiles)
                    send_log("Captcha resuelto")
                await page.wait_for_timeout(4000)
                await debug(page, "captcha_reduelto")
                send_log(f"📩 Esperando OTP para: {testC}")
            otp = wait_for_otp(testC)
            if otp:
                send_log(f"🔢 OTP: `{otp}`")
                await page.fill("#cvf-input-code", otp)
                await page.wait_for_timeout(3000)
                await debug(page, "otp_reduelto")
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_timeout(11000)
                await debug(page, "tel_otp")
                send_log("E8 - se obtuvo codigo")
                cookies = await context.cookies()
                with open("session.json", "w") as f: json.dump(cookies, f)
                with open("session.json", "rb") as f:
                    bot.send_document(CHAT_ID, f, caption=f"✅ Amazon Creada: {email}")
            else:
                send_log("❌ OTP no recibido.")
        except Exception as e:
            send_log(f"⚠️ Error: {str(e)}")
        finally:
            await browser.close()

# --- BOT INTERFACE ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "ZeuS Bot Online. Usa /crear para una cuenta Amazon.")

@bot.message_handler(commands=['crear'])
def run_cmd(message):
    bot.reply_to(message, "⚙️ Iniciando proceso...")
    asyncio.run(create_amazon())


@bot.message_handler(func=lambda m: True)
def handle_message(message):

    global captcha_answer

    captcha_answer = message.text

if __name__ == "__main__":
    send_log("🔥 Bot iniciado correctamente en Railway")
    bot.infinity_polling()
