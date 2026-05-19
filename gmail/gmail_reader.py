import imaplib
import email
import re
import time

from config import GMAIL_USER, GMAIL_APP_PASSWORD


def wait_for_otp(target_email, timeout=120):

    mail = imaplib.IMAP4_SSL("imap.gmail.com")

    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)

    start = time.time()

    while time.time() - start < timeout:

        mail.select("inbox")

        status, messages = mail.search(None, "ALL")

        mail_ids = messages[0].split()

        for mail_id in reversed(mail_ids[-10:]):

            status, msg_data = mail.fetch(mail_id, "(RFC822)")

            raw_email = msg_data[0][1]

            msg = email.message_from_bytes(raw_email)

            to_email = msg.get("To", "")

            if target_email.lower() not in to_email.lower():
                continue

            body = ""

            if msg.is_multipart():

                for part in msg.walk():

                    content_type = part.get_content_type()

                    if content_type == "text/plain":

                        body = part.get_payload(decode=True).decode(errors="ignore")

                        break

            else:

                body = msg.get_payload(decode=True).decode(errors="ignore")

            otp = re.search(r"\b(\d{6})\b", body)

            if otp:

                mail.logout()

                return otp.group(1)

        time.sleep(5)

    mail.logout()

    return None
