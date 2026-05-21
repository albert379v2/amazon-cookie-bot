from utils import send_log

async def handle_signin(page, email):

    await page.fill("#ap_email_login", email)

    await page.click("#continue")
    
async def handle_login_password(page):

    send_log("⚠️ Correo ya registrado")

    return False
