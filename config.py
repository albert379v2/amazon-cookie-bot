# config.py

import os

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
AC_KEY = os.getenv("AC_KEY")

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
