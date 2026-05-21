async def detect_state(page):

    text = await page.locator("body").inner_text()

    text = text.lower()

    # SIGNIN
    if "iniciar sesión o crear cuenta" in text:
        return "SIGNIN"

    # LOGIN EXISTENTE
    if "amazon contraseña" in text:
        return "LOGIN_PASSWORD"

    # NUEVA CUENTA
    if "parece que eres nuevo" in text:
        return "REGISTER_INTRO"

    # FORMULARIO
    if "nombre y apellido" in text:
        return "REGISTER_FORM"

    # CAPTCHA CANVAS
    if "elija todo" in text:
        return "CAPTCHA_CANVAS"

    # CAPTCHA ORBIT
    if "utiliza las flechas" in text:
        return "CAPTCHA_ORBIT"

    # OTP
    if "verifica la dirección de correo electrónico" in text:
        return "OTP_EMAIL"

    # SUCCESS
    if "mi cuenta" in text:
        return "SUCCESS"

    return "UNKNOWN"
