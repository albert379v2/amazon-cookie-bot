# config.py

import os

# === CONFIGURACIÓN ===
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
AC_KEY = os.getenv("AC_KEY")

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

PROXY_ADDR = os.getenv("PROXY_ADDR")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")


PROXY_CONFIG = {
    "server": f"http://{PROXY_ADDR}",
    "username": PROXY_USER,
    "password": PROXY_PASS
}

REQUESTS_PROXIES = {
    "http": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_ADDR}/",
    "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_ADDR}/"
}
