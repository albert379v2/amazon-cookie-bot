async def handle_register_intro(page):

    await page.click("#intention-submit-button")
    await page.wait_for_timeout(1000)


async def handle_register_form(page):

    await page.fill("#ap_customer_name", "Jhonatan aldama")

    await page.fill("#ap_password", "Admin.2026.!")

    await page.click("#continue")
    await page.wait_for_timeout(4000)
