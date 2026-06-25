import os
import json
import asyncio
import random
from playwright.async_api import async_playwright
import telebot

# ========== ENV ==========
TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID', 0))
PROXY_URL = os.getenv('PROXY_URL', '')

if not TOKEN:
    print("❌ BOT_TOKEN not found!"); exit(1)

bot = telebot.TeleBot(TOKEN)

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
async def launch_browser():
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

    if PROXY_URL:
        launch_opts["proxy"] = {"server": PROXY_URL}
        send_log(f"🌐 Proxy activo")
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
    send_log(f"🎯 Target: {email}")

    pw = browser = ctx = page = None
    try:
        pw, browser, ctx, page = await launch_browser()

        # 1. Navegar
        send_log("🚀 STEP 1: Navigate to Proton")
        await page.goto("https://account.proton.me/es/mail/signup?plan=free", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)
        await page.screenshot(path="s01_nav.png", full_page=True)
        send_photo("s01_nav.png", "📸 STEP 1: Page loaded")

        # 2. Username - MÉTODO IFRAME (Proton usa iframe para username)
        send_log(f"📝 STEP 2: Fill username: {username}")

        # Esperar a que cargue el iframe
        await asyncio.sleep(3)

        # Buscar iframe del username
        iframes = await page.query_selector_all('iframe')
        send_log(f"🔍 Found {len(iframes)} iframes")

        username_filled = False
        for i, iframe in enumerate(iframes):
            try:
                frame = await iframe.content_frame()
                if not frame:
                    continue

                # Buscar input en el iframe
                inp = await frame.query_selector('input[type="text"], input#username, input[name="username"]')
                if inp:
                    send_log(f"✅ Username input found in iframe {i}")
                    await human_type(frame, 'input', username)
                    await asyncio.sleep(1)

                    # Verificar que se escribió
                    val = await inp.input_value()
                    if val == username:
                        send_log(f"✅ Username filled via iframe: {val}")
                        username_filled = True
                        break
            except Exception as e:
                send_log(f"⚠️ Iframe {i} failed: {e}")

        # Fallback: JS directo en main frame
        if not username_filled:
            send_log("📝 Trying JS fallback for username...")
            try:
                result = await page.evaluate(f"""() => {{
                    const el = document.querySelector('input#username') || 
                               document.querySelector('input[name="username"]') ||
                               document.querySelector('iframe')?.contentDocument?.querySelector('input');
                    if (!el) return 'not_found';
                    const desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
                    if (desc && desc.set) {{
                        desc.set.call(el, '{username}');
                    }} else {{
                        el.value = '{username}';
                    }}
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    el.dispatchEvent(new KeyboardEvent('keyup', {{bubbles: true}}));
                    return el.value;
                }}""")
                send_log(f"✅ Username JS result: {result}")
                username_filled = (result == username)
            except Exception as e:
                send_log(f"❌ JS fallback failed: {e}")

        await asyncio.sleep(2)
        await page.screenshot(path="s02_user.png", full_page=True)
        send_photo("s02_user.png", f"📸 STEP 2: Username filled={username_filled}")

        if not username_filled:
            send_log("❌ Could not fill username")
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
            send_log(f"⚠️ Password fill issue: {e}")

        await page.screenshot(path="s03_pass.png", full_page=True)
        send_photo("s03_pass.png", "📸 STEP 3: Password filled")

        # 4. Submit
        send_log("📝 STEP 4: Click submit")
        await asyncio.sleep(random.uniform(1, 3))

        submit_clicked = False
        for btn_text in ["Comenzar", "Create", "Continue", "Continuar", "Sign up", "Registrarse"]:
            try:
                btn = await page.query_selector(f'button:has-text("{btn_text}")')
                if btn:
                    await human_click(page, f'button:has-text("{btn_text}")')
                    send_log(f"✅ Clicked: {btn_text}")
                    submit_clicked = True
                    break
            except:
                pass

        if not submit_clicked:
            try:
                await page.click('button[type="submit"]')
                submit_clicked = True
                send_log("✅ Clicked submit button")
            except:
                pass

        await asyncio.sleep(5)
        await page.screenshot(path="s04_submit.png", full_page=True)
        send_photo("s04_submit.png", f"📸 STEP 4: Submit clicked={submit_clicked}")

        # 5. Upsell
        send_log("🛒 STEP 5: Check upsell")
        await asyncio.sleep(3)

        for btn_text in ["No, thanks", "No, gracias", "Continue with free", "Get free"]:
            try:
                btn = await page.query_selector(f'button:has-text("{btn_text}")')
                if btn and await btn.is_visible():
                    await human_click(page, f'button:has-text("{btn_text}")')
                    send_log(f"✅ Upsell skipped: {btn_text}")
                    break
            except:
                pass

        await asyncio.sleep(3)
        await page.screenshot(path="s05_upsell.png", full_page=True)
        send_photo("s05_upsell.png", "📸 STEP 5: After upsell")

        # 6. Verification
        send_log("🔐 STEP 6: Check verification")
        await asyncio.sleep(3)

        has_verify = await page.evaluate("""() => {
            const t = document.body.innerText.toLowerCase();
            return t.includes('verification') || t.includes('verificación') ||
                   t.includes('human verification') || t.includes('verificación humana') ||
                   !!document.querySelector('input[type="email"]');
        }""")

        if has_verify:
            send_log("📧 Verification required")

            # Click email tab
            try:
                await human_click(page, 'button:has-text("Email")')
                await asyncio.sleep(2)
            except:
                pass

            # Fill verification email
            try:
                await human_type(page, 'input[type="email"]', email)
                await asyncio.sleep(1)
                await human_click(page, 'button:has-text("Send")')
                send_log("📧 Code sent")
            except:
                try:
                    await human_click(page, 'button:has-text("Enviar")')
                except:
                    pass

            await asyncio.sleep(3)
            await page.screenshot(path="s06_verify.png", full_page=True)
            send_photo("s06_verify.png", "📸 STEP 6: Verification email sent")

            # Wait OTP
            send_log("⏳ STEP 7: Waiting OTP...")
            bot.send_message(CHAT_ID, f"📩 Enter OTP for {email}:")
            otp = await wait_manual(timeout=180)
            if not otp:
                send_log("❌ OTP timeout")
                return

            send_log(f"🔢 OTP received: {otp}")
            await human_type(page, 'input[type="text"]', otp)
            await asyncio.sleep(1)

            try:
                await human_click(page, 'button:has-text("Verify")')
            except:
                try:
                    await human_click(page, 'button:has-text("Verificar")')
                except:
                    await page.keyboard.press('Enter')

            await asyncio.sleep(5)
            await page.screenshot(path="s07_otp.png", full_page=True)
            send_photo("s07_otp.png", "📸 STEP 7: OTP entered")
        else:
            send_log("✅ No verification needed")

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
                bot.send_photo(CHAT_ID, f, caption="❌ Failed - check screenshot")
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
        except:
            pass
    finally:
        if browser: await browser.close()
        if pw: await pw.stop()


# ========== TELEGRAM ==========
@bot.message_handler(commands=['start'])
def cmd_start(m):
    bot.reply_to(m, "🤖 Proton Bot\n/crear - Crear cuenta")

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
