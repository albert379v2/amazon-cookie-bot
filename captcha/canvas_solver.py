import re
import asyncio

captcha_answer = None


async def detect_canvas_captcha(page):

    text = await page.locator("body").inner_text()

    if "Elija todo" in text:
        return True

    if "Resuelve esta adivinanza" in text:
        return True

    if await page.locator("canvas").count() > 0:
        return True

    return False


async def capture_captcha(page):

    canvas = page.locator("canvas").first

    await canvas.screenshot(path="captcha.png")

    return "captcha.png"


async def click_captcha_tile(page, tile):

    canvas = page.locator("canvas").first

    box = await canvas.bounding_box()

    if not box:
        return

    cell_w = box["width"] / 3
    cell_h = box["height"] / 3

    # convierte 1-9 → 0-8
    tile -= 1

    row = tile // 3
    col = tile % 3

    x = box["x"] + (col * cell_w) + (cell_w / 2)
    y = box["y"] + (row * cell_h) + (cell_h / 2)

    await page.mouse.click(x, y)


async def solve_canvas_captcha(page, tiles):

    send_log(f"🎯 Resolviendo tiles: {tiles}")

    canvas = page.locator("canvas").first

    for i, tile in enumerate(tiles):

        await click_captcha_tile(page, tile)

        await page.wait_for_timeout(400)

        # debug visual opcional
        await canvas.screenshot(path=f"step_{i}.png")

    send_log("⏳ Esperando render final del canvas...")

    await page.wait_for_timeout(1500)

    await canvas.screenshot(path="captcha_selected.png")

    send_log("📸 Preview enviada")

    await page.wait_for_timeout(800)

    send_log("🚀 Enviando verificación...")

    await page.click("#amzn-btn-verify-internal")

    # 🔥 IMPORTANTÍSIMO: esperar resultado real
    await page.wait_for_timeout(4000)


def parse_tiles(text):

    numbers = re.findall(r"\d+", text)

    return [int(x) for x in numbers]


async def wait_captcha_response(timeout=120):

    global captcha_answer

    captcha_answer = None

    start = asyncio.get_event_loop().time()

    while True:

        if captcha_answer:

            response = captcha_answer

            captcha_answer = None

            return response

        if asyncio.get_event_loop().time() - start > timeout:

            return None

        await asyncio.sleep(1)


def set_captcha_answer(text):

    global captcha_answer

    captcha_answer = text
