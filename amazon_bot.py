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
    try:
        bot.send_message(CHAT_ID, f"🤖 {msg}", parse_mode="Markdown")
    except:
        pass
        
def send_screenshot(page, name):
    try:
        os.makedirs("/tmp", exist_ok=True)

        path = f"/tmp/{name}.png"
        page.screenshot(path=path, full_page=True)

        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=f"📸 {name}")

    except Exception as e:
        send_log(f"❌ Screenshot error: {e}")

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
            domain = self.session.get(f"{self.api}/domains").json()['hydra:member'][0]['domain']
            self.address = f"zeus{random.randint(1000,9999)}@{domain}"
            res = self.session.post(f"{self.api}/accounts", json={
                "address": self.address, "password": self.password
            }, timeout=25)
            
            auth = self.session.post(f"{self.api}/token", json={
                "address": self.address, "password": self.password
            }).json()
            self.token = auth['token']
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            return self.address
        except Exception as e:
            send_log(f"❌ Error Mail.tm: {e}")
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
    send_log("E1 - Inicializando MailTM")
    mail_service = MailTM()
    send_log("E2 - Obteniendo correo")
    email = mail_service.get_account()
    if not email: 
        send_log("ERR_MAIL_01")
        return
        send_log(f"E3 - Correo creado: {email}")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, proxy=PROXY_CONFIG)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0")
            page = await context.new_page()

            send_log(f"🚀 Creando: `{email}`")
            send_log("E7 - Entrando a Amazon")
            await page.goto(
    "https://www.amazon.com.mx/ap/signin?openid.return_to=https%3A%2F%2Fwww.amazon.com.mx%2F%3F_encoding%3DUTF8%26ref_%3Dnavm_hdr_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=anywhere_v2_mx&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0",
    wait_until="domcontentloaded",
    timeout=120000
)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1500)
            send_screenshot(page, "01_after_goto")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            if "/ax/claim" in page.url:
                send_log("⏳ Amazon en intent routing (esperando UI real)")
            await page.wait_for_function("""
            () => {
            return document.querySelector('#ap_email_login')
            || document.querySelector('#ap_email')
            || document.querySelector('#ap_customer_name')
            }
            """, timeout=30000)
            send_log(page.url)
            send_screenshot(page, "02_ax_claim")
        

            send_log("E8 - Amazon cargó")
            await solve_captcha(page)
            send_log("E9 - tiene captcha 1")

            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            send_log("F1")
            #await page.fill("#ap_email_login", email)
            await page.wait_for_selector("#ap_email_login, #ap_email", timeout=30000)
            email_input = page.locator("#ap_email_login, #ap_email")
            await email_input.fill(email)
            send_log("F2")
            #await page.click("#continue")
            await page.click("#continue")
            await page.wait_for_timeout(3000)
            if await page.locator("#ap_password").count() > 0:
                send_log("🔐 Cuenta existente → login flow")
                flow = "login"
            elif await page.locator("#ap_customer_name").count() > 0:
                send_log("🆕 Nueva cuenta → register flow")
                flow = "register"
            else:
                send_log("⚠️ Amazon no decidió flujo aún")
                flow = "unknown"
                if flow == "register":
                    await page.fill("#ap_customer_name", "Test User")
                    await page.fill("#ap_password", "Password123!")
            send_log("F2 vontinue1")
            await page.click("#intention-submit-button")
            send_log("Fllemar datos")
            await page.fill("#ap_customer_name", f"Zeus {random.randint(10,99)}")            
            send_log("F3")
            await page.fill("#ap_password", "Admin.2026.!")
            send_log("F4")
            ##await page.fill("#ap_password_check", "Admin.2026.!")
            send_log("F5 inicia click")
            await page.click("#auth-continue")
            ##await page.click("#continue")
            send_log("F6 click exitoso")
            send_log("E8 - se lleno formulario")
            send_log(page.url)
            await asyncio.sleep(5)
            await solve_captcha(page)
            send_log(page.url)
            send_log("E8 - captcha2")

            otp = await mail_service.wait_for_otp()
            if otp:
                send_log(f"🔢 OTP: `{otp}`")
                await page.fill("input[name='code']", otp)
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_timeout(11000)
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

if __name__ == "__main__":
    send_log("🔥 Bot iniciado correctamente en Railway")
    bot.infinity_polling()
