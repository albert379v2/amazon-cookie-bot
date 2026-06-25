import os
import json
import asyncio
import random
from playwright.async_api import async_playwright
import telebot

# ========== ENV ==========
TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID', 0))
PROXY_USER = os.getenv('PROXY_USER', '')
PROXY_PASS = os.getenv('PROXY_PASS', '')

if not TOKEN:
    print("❌ BOT_TOKEN not found!"); exit(1)

bot = telebot.TeleBot(TOKEN)

# ========== PROXY MANAGER ==========
class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current = None
        self.load_proxies()

    def load_proxies(self):
        """Carga proxies desde proxies.txt (formato IP:PORT por línea)"""
        for fname in ['proxies.txt', 'proxy.txt', 'proxies_list.txt']:
            if os.path.exists(fname):
                with open(fname, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and ':' in line and not line.startswith('#'):
                            self.proxies.append(line)
                print(f"✅ {len(self.proxies)} proxies cargados desde {fname}")
                return
        print("⚠️ No proxies.txt found")

    def get_random(self):
        """Devuelve proxy aleatorio diferente al último usado"""
        if not self.proxies:
            return None
        available = [p for p in self.proxies if p != self.current]
        if not available:
            available = self.proxies
        proxy = random.choice(available)
        self.current = proxy
        return proxy

    def get_socks5_url(self, proxy):
        """Construye URL socks5://user:pass@ip:port"""
        if not PROXY_USER or not PROXY_PASS:
            return f"http://{proxy}"
        return f"http://{PROXY_USER}:{PROXY_PASS}@{proxy}"

proxy_manager = ProxyManager()

# ========== UTILS ==========
def send_log(msg):
    print(f"[BOT] {msg}")
    try:
        bot.send_message(CHAT_ID, msg)
    except Exception as e:
        print(f"Telegram error: {e}")

def send_photo(path, caption=""):
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                bot.send_photo(CHAT_ID, f, caption=caption)
        except Exception as e:
            send_log(f"❌ Photo failed: {e}")

manual_response = None

def set_manual(text):
    global manual_response
    manual_response = text

async def wait_manual(timeout=180):
    global manual_response
    manual_response = None
    start = asyncio.get_event_loop().time()
    while True:
        if manual_response:
            r = manual_response; manual_response = None; return r
        if asyncio.get_event_loop().time() - start > timeout:
            return None
        await asyncio.sleep(1)

# ========== EMAIL ==========
def gen_email():
    names = ["alex", "maria", "carlos", "anna", "jose", "luis", "dani"]
    domains = ["mailgrid.shop", "tempmailo.com", "mail.tm"]
    return f"{random.choice(names)}{random.randint(1000,9999)}@{random.choice(domains)}"

# ========== BROWSER ==========
async def launch_browser(proxy_url=None):
    args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-gpu",
        "--window-size=1920,1080",
        "--disable-infobars",
        "--disable-extensions",
    ]

    launch_opts = {"headless": True, "args": args}

    if proxy_url:
        launch_opts["proxy"] = {"server": proxy_url}
        send_log(f"🌐 Proxy: {proxy_url.split('@')[1] if '@' in proxy_url else proxy_url}")
    else:
        send_log("⚠️ Sin proxy")

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(**launch_opts)

    ctx = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-ES",
        timezone_id="Europe/Madrid",
    )

    await ctx.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4]});
        Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en-US', 'en']});
        window.chrome = {runtime: {}};
    """)

    page = await ctx.new_page()
    return pw, browser, ctx, page

# ========== ACCIONES ==========
async def human_type(page, selector, text):
    for char in text:
        await page.type(selector, char, delay=random.randint(50, 150))
        if random.random() < 0.05:
            await page.keyboard.press('Backspace')
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.type(selector, char, delay=random.randint(50, 150))
        await asyncio.sleep(random.uniform(0.05, 0.15))

async def human_click(page, selector):
    if random.random() < 0.3:
        await page.hover(selector)
        await asyncio.sleep(random.uniform(0.2, 0.5))
    await page.click(selector)
    await asyncio.sleep(random.uniform(0.5, 1.5))

# ========== FLUJO PRINCIPAL ==========
async def run():
    email = gen_email()
    pwd = "Admin.2026.!"
    username = email.split('@')[0]

    # Obtener proxy aleatorio
    proxy = proxy_manager.get_random()
    proxy_url = proxy_manager.get_socks5_url(proxy) if proxy else None

    send_log(f"🎯 Target: {email}")
    if proxy:
        send_log(f"🌐 Using proxy: {proxy}")

    pw = browser = ctx = page = None
    try:
        pw, browser, ctx, page = await launch_browser(proxy_url)

        # 1. Navegar
        send_log("🚀 STEP 1: Navigate to Proton")
        await page.goto("https://account.proton.me/es/mail/signup?plan=free", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)
        await page.screenshot(path="s01_nav.png", full_page=True)
        send_photo("s01_nav.png", "📸 STEP 1: Page loaded")

        # 2. Username - IFRAME
        send_log(f"📝 STEP 2: Fill username: {username}")
        await asyncio.sleep(3)

        iframes = await page.query_selector_all('iframe')
        send_log(f"🔍 Found {len(iframes)} iframes")

        username_filled = False
        for i, iframe in enumerate(iframes):
            try:
                frame = await iframe.content_frame()
                if not frame: continue
                inp = await frame.query_selector('input[type="text"], input#username, input[name="username"]')
                if inp:
                    send_log(f"✅ Username input in iframe {i}")
                    await human_type(frame, 'input', username)
                    await asyncio.sleep(1)
                    val = await inp.input_value()
                    if val == username:
                        username_filled = True
                        send_log(f"✅ Username filled: {val}")
                        break
            except Exception as e:
                send_log(f"⚠️ Iframe {i}: {e}")

        # Fallback JS
        if not username_filled:
            send_log("📝 JS fallback...")
            try:
                result = await page.evaluate(f"""() => {{
                    const el = document.querySelector('input#username') || document.querySelector('input[name="username"]');
                    if (!el) return 'not_found';
                    const desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
                    if (desc && desc.set) desc.set.call(el, '{username}');
                    else el.value = '{username}';
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    el.dispatchEvent(new KeyboardEvent('keyup', {{bubbles: true}}));
                    return el.value;
                }}""")
                username_filled = (result == username)
                send_log(f"✅ JS result: {result}")
            except Exception as e:
                send_log(f"❌ JS failed: {e}")

        await asyncio.sleep(2)
        await page.screenshot(path="s02_user.png", full_page=True)
        send_photo("s02_user.png", f"📸 STEP 2: Username filled={username_filled}")
        if not username_filled:
            send_log("❌ Username failed")
            return

        # 3. Password
        send_log("📝 STEP 3: Fill password")
        try:
            await human_type(page, 'input#password', pwd)
            await asyncio.sleep(0.5)
            await human_type(page, 'input#password-confirm', pwd)
            await asyncio.sleep(1)
            send_log("✅ Password filled")
        except Exception as e:
            send_log(f"⚠️ Password: {e}")

        await page.screenshot(path="s03_pass.png", full_page=True)
        send_photo("s03_pass.png", "📸 STEP 3: Password")

        # 4. Submit
        send_log("📝 STEP 4: Click submit")
        await asyncio.sleep(random.uniform(1, 3))

        submit_clicked = False
        for btn_text in ["Comenzar", "Create", "Continue", "Continuar", "Sign up", "Registrarse"]:
            try:
                btn = await page.query_selector(f'button:has-text("{btn_text}")')
                if btn:
                    await human_click(page, f'button:has-text("{btn_text}")')
                    submit_clicked = True
                    send_log(f"✅ Clicked: {btn_text}")
                    break
            except: pass

        if not submit_clicked:
            try:
                await page.click('button[type="submit"]')
                submit_clicked = True
                send_log("✅ Clicked submit")
            except: pass

        await asyncio.sleep(5)
        await page.screenshot(path="s04_submit.png", full_page=True)
        send_photo("s04_submit.png", f"📸 STEP 4: Submit={submit_clicked}")

        # 5. Upsell
        send_log("🛒 STEP 5: Check upsell")
        await asyncio.sleep(3)
        for btn_text in ["No, thanks", "No, gracias", "Continue with free", "Get free"]:
            try:
                btn = await page.query_selector(f'button:has-text("{btn_text}")')
                if btn and await btn.is_visible():
                    await human_click(page, f'button:has-text("{btn_text}")')
                    send_log(f"✅ Upsell: {btn_text}")
                    break
            except: pass

        await asyncio.sleep(3)
        await page.screenshot(path="s05_upsell.png", full_page=True)
        send_photo("s05_upsell.png", "📸 STEP 5: Upsell")

        # 6. Verification
        send_log("🔐 STEP 6: Check verification")
        await asyncio.sleep(3)

        has_verify = await page.evaluate("""() => {
            const t = document.body.innerText.toLowerCase();
            return t.includes('verification') || t.includes('verificación') ||
                   t.includes('human verification') || t.includes('verificación humana') ||
                   !!document.querySelector('input[type="email"]');
        }""")

        if not has_verify:
            send_log("✅ No verification needed")
        else:
            send_log("📧 Verification detected")

            # Click email tab
            try:
                await human_click(page, 'button:has-text("Email")')
                await asyncio.sleep(2)
            except: pass

            # Fill verification email
            try:
                await human_type(page, 'input[type="email"]', email)
                await asyncio.sleep(1)
                send_log("✅ Verification email filled")
            except Exception as e:
                send_log(f"⚠️ Email fill: {e}")

            await page.screenshot(path="s06_email.png", full_page=True)
            send_photo("s06_email.png", "📸 STEP 6: Email filled")

            # CLICK BOTÓN OBTENER CÓDIGO
            send_log("📝 Clicking send code button...")
            code_sent = False

            selectors = [
                'button:has-text("Obtener código de verificación")',
                'button:has-text("Obtener código")',
                'button:has-text("Get verification code")',
                'button:has-text("Send code")',
                'button:has-text("Enviar código")',
                'button[type="submit"]',
            ]

            for sel in selectors:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        txt = await btn.inner_text()
                        await human_click(page, sel)
                        code_sent = True
                        send_log(f"✅ Clicked: {txt.strip()}")
                        break
                except: pass

            # JS fallback
            if not code_sent:
                try:
                    r = await page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('button'));
                        const b = btns.find(x => {
                            const t = x.innerText.trim().toLowerCase();
                            return t.includes('obtener') && t.includes('código') ||
                                   t.includes('get') && t.includes('code') ||
                                   t.includes('send') && t.includes('code');
                        });
                        if (b) { b.click(); return 'clicked: ' + b.innerText.trim(); }
                        return 'not_found';
                    }""")
                    send_log(f"JS button: {r}")
                    code_sent = ('not_found' not in r)
                except Exception as e:
                    send_log(f"JS fallback failed: {e}")

            await asyncio.sleep(3)
            await page.screenshot(path="s06_code_sent.png", full_page=True)
            send_photo("s06_code_sent.png", f"📸 STEP 6: Code sent={code_sent}")

            if not code_sent:
                send_log("❌ Could not click send code button")
                return

            # Wait OTP
            send_log("⏳ STEP 7: Waiting OTP...")
            bot.send_message(CHAT_ID, f"📩 Enter OTP for {email}:")
            otp = await wait_manual(timeout=180)
            if not otp:
                send_log("❌ OTP timeout")
                return

            send_log(f"🔢 OTP: {otp}")

            # Find OTP input
            otp_input_found = False
            otp_selectors = [
                'input[type="text"]',
                'input[placeholder*="código" i]',
                'input[placeholder*="code" i]',
                'input[maxlength="6"]',
                'input[data-testid*="verification" i]',
                'input[data-testid*="input" i]',
            ]

            for sel in otp_selectors:
                try:
                    inp = await page.query_selector(sel)
                    if inp and await inp.is_visible():
                        await human_type(page, sel, otp)
                        otp_input_found = True
                        send_log(f"✅ OTP filled via: {sel}")
                        break
                except: pass

            # JS fallback
            if not otp_input_found:
                try:
                    await page.evaluate(f"""() => {{
                        const inputs = Array.from(document.querySelectorAll('input'));
                        const inp = inputs.find(x => x.type === 'text' && (x.placeholder || '').toLowerCase().includes('código')) ||
                                     inputs.find(x => x.type === 'text');
                        if (inp) {{
                            inp.value = '{otp}';
                            inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                            inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                            return 'filled';
                        }}
                        return 'not_found';
                    }}""")
                    otp_input_found = True
                    send_log("✅ OTP filled via JS")
                except: pass

            if not otp_input_found:
                send_log("❌ Could not find OTP input")
                return

            await asyncio.sleep(1)

            # Click verify
            verify_clicked = False
            for sel in ['button:has-text("Verify")', 'button:has-text("Verificar")', 'button[type="submit"]']:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await human_click(page, sel)
                        verify_clicked = True
                        send_log("✅ Clicked verify")
                        break
                except: pass

            if not verify_clicked:
                await page.keyboard.press('Enter')
                send_log("✅ Pressed Enter")

            await asyncio.sleep(5)
            await page.screenshot(path="s07_otp.png", full_page=True)
            send_photo("s07_otp.png", "📸 STEP 7: OTP entered")

        # 8. Success check
        send_log("🔍 STEP 8: Check success")
        await asyncio.sleep(5)

        success = await page.evaluate("""() => {
            const t = document.body.innerText.toLowerCase();
            return t.includes('welcome') || t.includes('bienvenido') || 
                   t.includes('inbox') || t.includes('bandeja') ||
                   t.includes('tu cuenta está lista') ||
                   (!!document.querySelector('[data-testid="inbox"]'));
        }""")

        await page.screenshot(path="s08_final.png", full_page=True)

        if success:
            cookies = await ctx.cookies()
            fn = f"session_{email.replace('@','_').replace('.','_')}.json"
            with open(fn, "w") as f:
                json.dump(cookies, f, indent=2)

            with open(fn, "rb") as f:
                bot.send_document(CHAT_ID, f, caption=f"✅ Account: {email}")

            with open("s08_final.png", "rb") as f:
                bot.send_photo(CHAT_ID, f, caption="✅ SUCCESS")

            send_log(f"✅ DONE: {email}")
        else:
            with open("s08_final.png", "rb") as f:
                bot.send_photo(CHAT_ID, f, caption="❌ Failed")
            send_log("❌ Failed")

    except Exception as e:
        send_log(f"❌ ERROR: {str(e)[:500]}")
        import traceback
        send_log(traceback.format_exc()[:1000])
        try:
            if page:
                await page.screenshot(path="error.png", full_page=True)
                with open("error.png", "rb") as f:
                    bot.send_photo(CHAT_ID, f, caption=f"❌ Error: {str(e)[:200]}")
        except: pass
    finally:
        if browser: await browser.close()
        if pw: await pw.stop()


# ========== TELEGRAM ==========
@bot.message_handler(commands=['start'])
def cmd_start(m):
    bot.reply_to(m, 
        "🤖 Proton Bot\n\n"
        "📋 Variables de entorno:\n"
        "PROXY_USER=usuario\n"
        "PROXY_PASS=contraseña\n\n"
        "Crear archivo proxies.txt con:\n"
        "IP:PORT (uno por línea)\n\n"
        "/crear - Crear cuenta con proxy aleatorio"
    )

@bot.message_handler(commands=['crear'])
def cmd_crear(m):
    bot.reply_to(m, "⚙️ Iniciando...")
    asyncio.run(run())

@bot.message_handler(func=lambda m: True)
def cmd_text(m):
    set_manual(m.text)

# ========== ENTRY ==========
if __name__ == "__main__":
    send_log("🔥 Bot started")
    import threading
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    import time
    while True:
        time.sleep(1)
