from utils import send_log

async def detect_state(page):
    if await page.locator("#cvf-aamation-challenge-iframe").count() > 0:
        return "CAPTCHA_DETECTED"

    # LOGIN
    if await page.locator("#ap_email_login").count() > 0:
        return "SIGNIN"

    # REGISTER INTRO
    if await page.locator("text=Proceder a crear una cuenta").count() > 0:
        return "REGISTER_INTRO"

    # REGISTER FORM
    if await page.locator("input[name='customerName']").count() > 0:
        return "REGISTER_FORM"

    # OTP EMAIL
    if await page.locator("#cvf-input-code").count() > 0:
        return "OTP_EMAIL"


    # CAPTCHA CANVAS
    if await page.locator("canvas").count() > 0:
        return "CAPTCHA_CANVAS"

    # CAPTCHA ORBIT
    if await page.locator("text=Iniciar rompecabezas").count() > 0:
        return "CAPTCHA_ORBIT"

    # SUCCESS
    if await page.locator("#nav-link-accountList").count() > 0:
        return "SUCCESS"

    return "UNKNOWN"
