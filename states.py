from utils import send_log

async def detect_state(page):

    # LOGIN
    if await page.locator("#ap_email_login").count() > 0:
        return "SIGNIN"

    # REGISTER INTRO
    if await page.locator("text=Proceder a crear una cuenta").count() > 0:
        return "REGISTER_INTRO"

    # DETECTAR PUZZLE INTERNO
    for frame in page.frames:

        try:

            text = (await frame.locator("body").inner_text()).lower()

            if "hazla coincidir" in text:
                return "CAPTCHA_ORBIT_GAME"

            if "utiliza las flechas" in text:
                return "CAPTCHA_ORBIT_GAME"

            if "envíe" in text:
                return "CAPTCHA_ORBIT_GAME"

            if "arrastra" in text:
                return "CAPTCHA_ORBIT_GAME"

        except:
            pass

    # CAPTCHA GENERAL
    if await page.locator("#cvf-aamation-challenge-iframe").count() > 0:
        return "CAPTCHA_DETECTED"

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
