async def detect_state(page):

    text = (await page.locator("body").inner_text()).lower()
    if "resuelve esta adivinanza" in text:
        return "CAPTCHA_DETECTED"
    # LOGIN EXISTENTE
    if "amazon contraseña" in text:
        return "LOGIN_PASSWORD"

    # REGISTER INTRO
    if "parece que eres nuevo en amazon" in text:
        return "REGISTER_INTRO"

    # REGISTER FORM
    if (
        "crear cuenta" in text
        and "nombre y apellido" in text
    ):
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
    # OTP TELEFONO
    if "agregar un número de teléfono móvil" in text:
        return "OTP_PHONE"

    # SIGNIN (SIEMPRE AL FINAL)
    if (
        "ingresa el número de celular" in text
        and "continuar" in text
    ):
        return "SIGNIN"
    
    
    return "UNKNOWN"
