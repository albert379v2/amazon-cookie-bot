async def detect_state(page):

    text = (await page.locator("body").inner_text()).lower()

    # LOGIN EXISTENTE
    if "amazon contraseña" in text:
        return "LOGIN_PASSWORD"

    # SIGNIN
    if "ingresa el número de celular" in text:
        return "SIGNIN"

    # NUEVA CUENTA
    if "parece que eres nuevo en amazon" in text:
        return "REGISTER_INTRO"

    # FORMULARIO
    if "crear cuenta" in text and "nombre y apellido" in text:
        return "REGISTER_FORM"

    # CAPTCHA CANVAS
    if "elija todo" in text:
        return "CAPTCHA_CANVAS"

    # CAPTCHA ORBIT
    if "utiliza las flechas" in text:
        return "CAPTCHA_ORBIT"

    # OTP EMAIL
    if "verifica la dirección de correo electrónico" in text:
        return "OTP_EMAIL"

    # SUCCESS
    if "mi cuenta" in text:
        return "SUCCESS"

    return "UNKNOWN"
