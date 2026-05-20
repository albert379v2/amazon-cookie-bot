async def detect_state(page):

    text = await page.locator("body").inner_text()

    # LOGIN EXISTENTE
    if "Amazon contraseña" in text:
        return "LOGIN_PASSWORD"

    # NUEVA CUENTA
    if "Parece que eres nuevo en Amazon" in text:
        return "REGISTER_INTRO"

    # FORMULARIO
    if "Crear cuenta" in text and "Nombre y apellido" in text:
        return "REGISTER_FORM"

    # CAPTCHA CANVAS
    if "Elija todo" in text:
        return "CAPTCHA_CANVAS"

    # CAPTCHA ORBITAS
    if "Utiliza las flechas" in text:
        return "CAPTCHA_ORBIT"

    # OTP
    if "Verifica la dirección de correo electrónico" in text:
        return "OTP_EMAIL"

    # SUCCESS
    if "Mi cuenta" in text:
        return "SUCCESS"

    return "UNKNOWN"
