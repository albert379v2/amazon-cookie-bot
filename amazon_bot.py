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


# === CONFIGURACIÓN ===
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
AC_KEY = os.getenv("AC_KEY")

PROXY_ADDR = os.getenv("PROXY_ADDR")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

print("TOKEN:", TOKEN)
print("CHAT_ID:", CHAT_ID)
print("PROXY_ADDR:", PROXY_ADDR)
print("PROXY_USER:", PROXY_USER)
print("PROXY_PASS:", PROXY_PASS)

PROXY_CONFIG = {
    "server": f"http://{PROXY_ADDR}",
    "username": PROXY_USER,
    "password": PROXY_PASS
}

REQUESTS_PROXIES = {
    "http": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_ADDR}/",
    "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_ADDR}/"
}

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try: bot.send_message(CHAT_ID, f"🤖 {msg}", parse_mode="Markdown")
    except: pass

# --- MANEJO DE CORREO (MAIL.TM API) ---
class MailTM:
    def __init__(self):
        self.api = "https://api.mail.tm"
        self.session = requests.Session()
        #self.session.proxies = REQUESTS_PROXIES
        self.address = ""
        self.password = "ZeusBot2026!"
        self.token = ""

    def get_account(self):
        try:
            send_log("📡 Obteniendo dominios MailTM")

        r = self.session.get(f"{self.api}/domains", timeout=20)
        data = r.json()
        send_log(f"DOMAINS RESPONSE: {data}")

        domain = data['hydra:member'][0]['domain']

        self.address = f"zeus{random.randint(1000,9999)}@{domain}"

        send_log(f"📧 Creando cuenta: {self.address}")

        res = self.session.post(f"{self.api}/accounts", json={
            "address": self.address,
            "password": self.password
        }, timeout=25)

        send_log(f"ACCOUNT RESPONSE: {res.text}")

        auth = self.session.post(f"{self.api}/token", json={
            "address": self.address,
            "password": self.password
        }).json()

        self.token = auth['token']
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

        send_log("✅ MailTM listo")

        return self.address

    except Exception as e:
        send_log(f"❌ ERROR MAILTM: {str(e)}")
        return None

    async def wait_for_otp(self):
        send_log("📩 Esperando OTP en Mail.tm...")
        for _ in range(20):
            await asyncio.sleep(8)
            try:
                #msgs_data = self.session.get(f"{self.api}/messages").json()
                #send_log(str(msgs_data))
                msgs = self.session.get(f"{self.api}/messages").json()['hydra:member']
                if msgs:
                    msg_id = msgs[0]['id']
                    content = self.session.get(f"{self.api}/messages/{msg_id}").json()['text']
                    otp = re.search(r'(\d{6})', content)
                    if otp: return otp.group(1)
            except: continue
        return None

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
    send_log("🚀 Iniciando flujo limpio de registro")

    mail_service = MailTM()
    email = mail_service.get_account()

    if not email:
        send_log("❌ No se pudo crear correo")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # importante para estabilidad en Amazon
            proxy=PROXY_CONFIG
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            locale="es-MX"
        )

        page = await context.new_page()

        # 🟢 1. IR DIRECTO A REGISTRO
        send_log("🌐 Abriendo registro Amazon")
        await page.goto("https://www.amazon.com.mx/ap/register", wait_until="domcontentloaded")

        await page.wait_for_timeout(2000)

        await page.screenshot(path="step1.png")

        # 🛡️ CAPTCHA (si aparece)
        await solve_captcha(page)

        # 🟡 2. LLENAR EMAIL
        send_log("📧 Ingresando email")

        email_input = page.locator("#ap_customer_name, #ap_email")
        await page.wait_for_selector("#ap_email", timeout=20000)
        await page.fill("#ap_email", email)

        await page.click("#continue")

        # 🔁 esperar transición real
        await page.wait_for_load_state("networkidle")

        await page.screenshot(path="step2.png")

        # 🟠 3. VERIFICAR SI PASÓ A FORMULARIO DE REGISTRO
        send_log("🧾 Cargando formulario de cuenta")

        # nombre
        if await page.locator("#ap_customer_name").count() > 0:
            await page.fill("#ap_customer_name", f"Zeus {random.randint(10,99)}")

        # password
        if await page.locator("#ap_password").count() > 0:
            await page.fill("#ap_password", "Admin.2026.!")

        # confirmar password (si existe)
        if await page.locator("#ap_password_check").count() > 0:
            await page.fill("#ap_password_check", "Admin.2026.!")

        await page.screenshot(path="step3.png")

        # 🟢 4. SUBMIT REGISTRO
        send_log("📨 Enviando registro")

        continue_btn = page.locator("#auth-continue, #continue, input[type='submit']")
        await continue_btn.first.click()

        await page.wait_for_timeout(5000)

        await solve_captcha(page)

        send_log(f"URL actual: {page.url}")

        # 🔵 5. OTP
        send_log("📩 Esperando OTP")

        otp = await mail_service.wait_for_otp()

        if not otp:
            send_log("❌ OTP no recibido")
            await browser.close()
            return

        send_log(f"🔢 OTP recibido: {otp}")

        otp_input = page.locator("input[name='code'], #cvf-input-code")
        await otp_input.fill(otp)

        submit_otp = page.locator("#cvf-submit-otp-button, input[type='submit']")
        await submit_otp.first.click()

        await page.wait_for_timeout(8000)

        # 🍪 guardar sesión
        cookies = await context.cookies()
        with open("session.json", "w") as f:
            json.dump(cookies, f)

        send_log("✅ Registro completado")

        with open("session.json", "rb") as f:
            bot.send_document(CHAT_ID, f, caption=f"✅ Cuenta creada: {email}")

        await browser.close()

# --- BOT INTERFACE ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "ZeuS Bot Online. Usa /crear para una cuenta Amazon.")

@bot.message_handler(commands=['crear'])
def run_cmd(message):
    bot.reply_to(message, "⚙️ Iniciando proceso...")
    asyncio.run(create_amazon())

if __name__ == "__main__":
    send_log("🔥 Bot iniciado correctamente en Railway")
    bot.infinity_polling()
