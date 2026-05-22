from utils import send_log

async def detect_state(page):
    send_log(page.url)
    text = (await page.locator("body").inner_text()).lower()
    send_log(f"DEBUG CAPTCHA => {'adivinanza' in text}")
    if "resuelve esta adivinanza" in text:
        return "CAPTCHA_DETECTED"

    # SIGNIN
    if await page.locator("#ap_email_login").count() > 0:
        return "SIGNIN"

    # REGISTER INTRO
    if await page.locator("text=Proceder a crear una cuenta").count() > 0:
        return "REGISTER_INTRO"

    # REGISTER FORM
    if await page.locator("input[name='customerName']").count() > 0:
        return "REGISTER_FORM"

    # CAPTCHA CANVAS
    if await page.locator("canvas").count() > 0:
        return "CAPTCHA_CANVAS"

    # CAPTCHA ORBIT
    if await page.locator("text=rompecabezas").count() > 0:
        return "CAPTCHA_ORBIT"

    # OTP EMAIL
    if await page.locator("#cvf-input-code").count() > 0:
        return "OTP_EMAIL"

    # OTP PHONE
    text = (await page.locator("body").inner_text()).lower()

    if "agregar un número de teléfono móvil" in text:
        return "OTP_PHONE"

    # SUCCESS
    if "mi cuenta" in text:
        return "SUCCESS"

    return "UNKNOWN"
