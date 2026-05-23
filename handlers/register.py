async def handle_register_intro(page):
    send_log("✍️ entrando pagina de registro o login")

    await page.click("#intention-submit-button")
    await page.wait_for_timeout(1000)
    send_log("✍️ saliendo registro login")


async def handle_register_form(page):
    send_log("✍️ ingresando registro")

    await page.fill("#ap_customer_name", "Jhonatan aldama")
    send_log("✍️ Insertando nombre")
    await page.fill("#ap_password", "Admin.2026.!")

    await page.click("#continue")
    send_log("✍️ trrmino ingresar información")
    await page.wait_for_timeout(4000)
